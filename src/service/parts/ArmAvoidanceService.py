# -*- coding: utf-8 -*-
#
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from mmd.PmxData import PmxModel, Bone # noqa
from mmd.VmdData import VmdMotion, VmdBoneFrame, VmdCameraFrame, VmdInfoIk, VmdLightFrame, VmdMorphFrame, VmdShadowFrame, VmdShowIkFrame # noqa
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from module.MOptions import MOptions, MOptionsDataSet # noqa
from module.MParams import BoneLinks # noqa
from utils import MUtils, MServiceUtils, MBezierUtils # noqa
from utils.MLogger import MLogger # noqa
from utils.MException import SizingException

logger = MLogger(__name__, level=1)

# 床処理用INDEX
FLOOR_IDX = -1


# 接触回避用オプション
class ArmAvoidanceOption():

    def __init__(self, arm_links: BoneLinks, ik_links_list: list, ik_count_list: list, avoidance_links: dict, avoidances: dict):
        super().__init__()

        self.arm_links = arm_links
        self.ik_links_list = ik_links_list
        self.ik_count_list = ik_count_list
        self.avoidance_links = avoidance_links
        self.avoidances = avoidances


class ArmAvoidanceService():
    def __init__(self, options: MOptions):
        self.options = options

    def execute(self):
        # 腕処理対象データセットを取得
        self.target_data_set_idxs = self.get_target_set_idxs()
        logger.test("target_data_set_idxs: %s", self.target_data_set_idxs)

        if len(self.target_data_set_idxs) == 0:
            # データセットがない場合、処理スキップ
            logger.warning("接触回避ができるファイルセットが見つからなかったため、処理をスキップします。", decoration=MLogger.DECORATION_BOX)
            return True

        futures = []
        with ThreadPoolExecutor(thread_name_prefix="avoidance", max_workers=1) as executor:
            for data_set_idx, data_set in enumerate(self.options.data_set_list):
                logger.info("接触回避　【No.%s】", (data_set_idx + 1), decoration=MLogger.DECORATION_LINE)

                futures.append(executor.submit(self.execute_avoidance_pool, data_set_idx, "左"))
                futures.append(executor.submit(self.execute_avoidance_pool, data_set_idx, "右"))

        concurrent.futures.wait(futures, timeout=None, return_when=concurrent.futures.FIRST_EXCEPTION)

        result = True

        for f in futures:
            result = f.result() and result
    
        return result

    # 接触回避実行（先頭からキーフレ単位で見ていく必要があるので、並列化不可）
    def execute_avoidance_pool(self, data_set_idx: int, direction: str):
        try:
            logger.copy(self.options)
            # 処理対象データセット
            data_set = self.options.data_set_list[data_set_idx]

            # 接触回避用準備
            avoidance_options = self.prepare_avoidance(data_set_idx, direction)

            prev_fno = 0
            fnos = data_set.motion.get_bone_fnos("{0}腕".format(direction), "{0}ひじ".format(direction), "{0}手首".format(direction))
            while len(fnos) > 0:
                fno = fnos[0]
                self.execute_avoidance_frame(data_set_idx, direction, avoidance_options, fno)

                if fno // 500 > prev_fno and fnos[-1] > 0:
                    logger.info("-- %sフレーム目:終了(%s％)【No.%s-%s】", fno, round((fno / fnos[-1]) * 100, 3), data_set_idx + 1, direction)
                    prev_fno = fno // 500
                
                # キーの登録が増えているかもなので、ここで取り直す
                fnos = data_set.motion.get_bone_fnos("{0}腕".format(direction), "{0}ひじ".format(direction), "{0}手首".format(direction), start_fno=(fno + 1))

            return True
        except SizingException as se:
            logger.error("サイジング処理が処理できないデータで終了しました。\n\n%s", se.message)
            return False
        except Exception as e:
            logger.error("サイジング処理が意図せぬエラーで終了しました。", e)
            return False

    # フレーム単位の接触回避処理
    def execute_avoidance_frame(self, data_set_idx: int, direction: str, avoidance_options: ArmAvoidanceOption, fno: int):
        # 処理対象データセット
        data_set = self.options.data_set_list[data_set_idx]

        for ((avoidance_name, avodance_link), avoidance) in zip(avoidance_options.avoidance_links.items(), avoidance_options.avoidances.values()):
            # 剛体の現在位置をチェック
            rep_avbone_global_3ds, rep_avbone_global_mats = \
                MServiceUtils.calc_global_pos(data_set.rep_model, avodance_link, data_set.motion, fno, return_matrix=True)

            obb = avoidance.get_obb(avodance_link.get(avodance_link.last_name()).position, rep_avbone_global_mats, direction == "左")

            # 剛体の原点 ---------------
            debug_bone_name = "右1"

            debug_bf = VmdBoneFrame(fno)
            debug_bf.key = True
            debug_bf.set_name(debug_bone_name)
            debug_bf.position = obb.origin
            
            if debug_bone_name not in data_set.motion.bones:
                data_set.motion.bones[debug_bone_name] = {}
            
            data_set.motion.bones[debug_bone_name][fno] = debug_bf

            # 変更前のbf（オリジナルモーションではなく、スタンス補正後なので、この時点のを保持）
            org_bfs = {}
            for arm_link in avoidance_options.arm_links:
                for ik_links in avoidance_options.ik_links_list[arm_link.last_name()]:
                    for link_name in ik_links.all().keys():
                        if link_name not in org_bfs:
                            org_bfs[link_name] = data_set.motion.calc_bf(link_name, fno).copy()

            collision = False
            is_success = []
            for arm_link in avoidance_options.arm_links:

                # 先モデルのそれぞれのグローバル位置
                rep_global_3ds = MServiceUtils.calc_global_pos(data_set.rep_model, arm_link, data_set.motion, fno)

                # [logger.debug("k: %s, v: %s", k, v) for k, v in rep_global_3ds.items()]

                collision, rep_collision_vec = obb.judge_collision(rep_global_3ds[arm_link.last_name()])
                logger.test("d: %s-%s, f: %s, col: %s, ret: %s", data_set_idx, direction, fno, collision, rep_collision_vec.to_log())

                # FIXME DEBUG ------------------
                # 元の先端ボーン位置 -------------
                debug_bone_name = "{0}2".format(arm_link.last_name()[0])

                debug_bf = VmdBoneFrame(fno)
                debug_bf.key = True
                debug_bf.set_name(debug_bone_name)
                debug_bf.position = rep_global_3ds[arm_link.last_name()]
                
                if debug_bone_name not in data_set.motion.bones:
                    data_set.motion.bones[debug_bone_name] = {}
                
                data_set.motion.bones[debug_bone_name][fno] = debug_bf
                # ----------
                
                if collision:
                    logger.info("○接触あり: f: %s(%s-%s:%s), 元: %s, 回避: %s", fno, \
                                (data_set_idx + 1), arm_link.last_name(), avoidance_name, rep_global_3ds[arm_link.last_name()].to_log(), rep_collision_vec.to_log())

                    # IK処理実行
                    for ik_cnt, (ik_links, ik_max_count) in enumerate(zip(avoidance_options.ik_links_list[arm_link.last_name()], avoidance_options.ik_count_list[arm_link.last_name()])):
                        # IK計算実行
                        MServiceUtils.calc_IK(data_set.rep_model, arm_link, data_set.motion, fno, rep_collision_vec, ik_links, max_count=ik_max_count)

                        # 現在のエフェクタ位置
                        rep_global_3ds = MServiceUtils.calc_global_pos(data_set.rep_model, arm_link, data_set.motion, fno)
                        now_rep_effector_pos = rep_global_3ds[arm_link.last_name()]

                        # 現在のエフェクタ位置との差分
                        rep_diff = rep_collision_vec - now_rep_effector_pos

                        # for link_name, link_bone in ik_links.all().items():
                        #     logger.debug("(%s): f: %s(%s:%s:%s), org: %s", ik_cnt, fno, (data_set_idx + 1), \
                        #                  link_name, avoidance_name, org_bfs[link_name].rotation.toEulerAngles4MMD().to_log())
                        
                        # IKの関連ボーンの内積チェック
                        dot_dict = {}
                        dot_limit_dict = {}
                        for link_name, link_bone in ik_links.all().items():
                            dot_dict[link_name] = MQuaternion.dotProduct(org_bfs[link_name].rotation, data_set.motion.calc_bf(link_name, fno).rotation)
                            dot_limit_dict[link_name] = link_bone.dot_limit

                        if (np.count_nonzero(np.where(np.abs(rep_diff.data()) > 2, 1, 0)) == 0 and \
                                np.count_nonzero(np.where(np.abs(np.array(list(dot_dict.values()))) < np.array(list(dot_limit_dict.values())), 1, 0)) == 0):
                            logger.debug("☆接触回避実行成功(%s): f: %s(%s:%s:%s), new: %s, now: %s, vec: %s, dot: %s", ik_cnt, fno, (data_set_idx + 1), \
                                         list(ik_links.all().keys()), avoidance_name, rep_collision_vec.to_log(), now_rep_effector_pos.to_log(), rep_diff.to_log(), list(dot_dict.values()))

                            # 大体同じ位置にあって、角度もそう大きくズレてない場合、OK
                            is_success.append(True)

                            # 回避後の先端ボーン位置 -------------
                            debug_bone_name = "{0}3".format(arm_link.last_name()[0])

                            debug_bf = VmdBoneFrame(fno)
                            debug_bf.key = True
                            debug_bf.set_name(debug_bone_name)
                            debug_bf.position = rep_collision_vec
                            
                            if debug_bone_name not in data_set.motion.bones:
                                data_set.motion.bones[debug_bone_name] = {}
                            
                            data_set.motion.bones[debug_bone_name][fno] = debug_bf
                            # ----------

                            # 成功していたら、オリジナルとして再保持
                            for link_name in ik_links.all().keys():
                                org_bfs[link_name] = data_set.motion.calc_bf(link_name, fno).copy()

                            break
                        else:
                            logger.debug("★接触回避実行失敗(%s): f: %s(%s:%s:%s), new: %s, now: %s, vec: %s, dot: %s", ik_cnt, fno, (data_set_idx + 1), \
                                         list(ik_links.all().keys()), avoidance_name, rep_collision_vec.to_log(), now_rep_effector_pos.to_log(), rep_diff.to_log(), list(dot_dict.values()))

                            # 失敗していたら一旦元に戻す
                            is_success.append(False)
                            for link_name in list(ik_links.all().keys())[1:]:
                                data_set.motion.bones[link_name][fno].rotation = org_bfs[link_name].rotation.copy()
                else:
                    # 衝突していなければ成功
                    for ik_links in avoidance_options.ik_links_list[arm_link.last_name()]:
                        for link_name in list(ik_links.all().keys())[1:]:
                            bf = data_set.motion.calc_bf(link_name, fno)
                            data_set.motion.bones[link_name][fno] = bf
                            org_bfs[link_name] = bf.copy()
                        
            if len(is_success) > 0 and is_success.count(False) > 0:
                # どこかのパターンで失敗してる場合、失敗ログ
                logger.info("×回避失敗: f: %s(%s-%s:%s)", fno, (data_set_idx + 1), direction, avoidance_name)
                    
        # どっちにしろbf確定
        for arm_link in avoidance_options.arm_links:
            for ik_links in avoidance_options.ik_links_list[arm_link.last_name()]:
                for link_name in list(ik_links.all().keys())[1:]:
                    data_set.motion.regist_bf(data_set.motion.calc_bf(link_name, fno), link_name, fno)

    # 接触回避の準備
    def prepare_avoidance(self, data_set_idx: int, direction: str):
        data_set = self.options.data_set_list[data_set_idx]

        avoidance_links = {}
        avoidances = {}
        
        if "頭接触回避" in self.options.arm_options.avoidance_target_list:
            # 頭接触回避用剛体取得
            head_rigidbody = data_set.rep_model.get_head_rigidbody()

            if head_rigidbody:
                logger.info("【No.%s-%s】頭接触回避用剛体: 半径: %s, 位置: %s", (data_set_idx + 1), direction, head_rigidbody.shape_size.x(), head_rigidbody.shape_position.to_log())
                avoidance_links[head_rigidbody.name] = data_set.rep_model.create_link_2_top_one(data_set.rep_model.bone_indexes[head_rigidbody.bone_index])
                avoidances[head_rigidbody.name] = head_rigidbody
            else:
                logger.info("【No.%s-%s】頭にウェイトが乗っている頂点が見つからなかった為、接触回避用剛体が作れませんでした。", (data_set_idx + 1), direction)
        
        logger.debug("list: %s", self.options.arm_options.avoidance_target_list)
        for avoidance_target in self.options.arm_options.avoidance_target_list:
            if avoidance_target and len(avoidance_target) > 0:
                for rigidbody_name, rigidbody in data_set.rep_model.rigidbodies.items():
                    # 処理対象剛体：剛体名が指定の文字列を含んでおり、かつボーン追従剛体
                    if avoidance_target in rigidbody_name and rigidbody.isModeStatic() and rigidbody.bone_index in data_set.rep_model.bone_indexes:
                        # 追従するボーンINDEXのリンク
                        avoidance_links[rigidbody_name] = data_set.rep_model.create_link_2_top_one(data_set.rep_model.bone_indexes[rigidbody.bone_index])
                        avoidances[rigidbody_name] = rigidbody
                        rigidbody.bone_name = data_set.rep_model.bone_indexes[rigidbody.bone_index]
                        rigidbody.is_arm_upper = rigidbody.shape_position.y() > data_set.rep_model.bones["右腕"].position.y()

                        logger.debug("%s-%s, %s: %s", data_set_idx, direction, rigidbody_name, rigidbody)

                        logger.info("【No.%s】判定対象剛体「%s」", (data_set_idx + 1), rigidbody_name)

        # グローバル位置計算用リンク
        arm_links = []
        # IK用リンク（エフェクタから追加していく）
        ik_links_list = {}
        ik_count_list = {}

        effector_bone_name_list = []
        effector_bone_name_list.append("{0}ひじ".format(direction))
        effector_bone_name_list.append("{0}ひじ手首中間".format(direction))

        # 腕を動かすパターン
        for effector_bone_name in effector_bone_name_list:
            # 末端までのリンク
            arm_link = data_set.rep_model.create_link_2_top_one(effector_bone_name)
            arm_links.append(arm_link)

            ik_links_list[effector_bone_name] = []
            ik_count_list[effector_bone_name] = []

            effector_bone = arm_link.get(effector_bone_name)

            arm_bone = arm_link.get("{0}腕".format(direction))
            arm_bone.dot_limit = 0.75

            ik_links = BoneLinks()
            ik_links.append(effector_bone)
            ik_links.append(arm_bone)
            ik_links_list[effector_bone_name].append(ik_links)
            ik_count_list[effector_bone_name].append(3)

        effector_bone_name_list = []

        effector_bone_name_list.append("{0}手首".format(direction))
        if "{0}人指先".format(direction) in data_set.rep_model.bones:
            effector_bone_name_list.append("{0}人指先".format(direction))

        # ひじも動かすパターン
        for effector_bone_name in effector_bone_name_list:
            # 末端までのリンク
            arm_link = data_set.rep_model.create_link_2_top_one(effector_bone_name)
            arm_links.append(arm_link)

            ik_links_list[effector_bone_name] = []
            ik_count_list[effector_bone_name] = []

            effector_bone = arm_link.get(effector_bone_name)

            # ひじは角度制限をつける
            elbow_bone = arm_link.get("{0}ひじ".format(direction))
            # elbow_bone.ik_limit_min = MVector3D(-180, -0.5, -90)
            # elbow_bone.ik_limit_max = MVector3D(180, 180, 90)
            elbow_bone.dot_limit = 0.75

            arm_bone = arm_link.get("{0}腕".format(direction))
            arm_bone.dot_limit = 0.75

            ik_links = BoneLinks()
            ik_links.append(effector_bone)
            ik_links.append(elbow_bone)
            ik_links.append(arm_bone)
            ik_links_list[effector_bone_name].append(ik_links)
            ik_count_list[effector_bone_name].append(3)

        # 手首リンク登録
        return ArmAvoidanceOption(arm_links, ik_links_list, ik_count_list, avoidance_links, avoidances)

    # 処理対象データセットINDEX取得
    def get_target_set_idxs(self):
        target_data_set_idxs = []
        for data_set_idx, data_set in enumerate(self.options.data_set_list):
            if data_set.motion.motion_cnt <= 0:
                # モーションデータが無い場合、処理スキップ
                continue
            
            if (self.options.arm_options.arm_check_skip_flg or (data_set.rep_model.can_arm_sizing and data_set.org_model.can_arm_sizing)) \
                    and data_set_idx not in target_data_set_idxs:
                # ボーンセットがあり、腕系サイジング可能で、かつまだ登録されていない場合
                target_data_set_idxs.append(data_set_idx)
            
        return target_data_set_idxs

