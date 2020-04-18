# -*- coding: utf-8 -*-
#
import copy
import struct
from module.MMath import MRect, MVector2D, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from utils import MBezierUtils # noqa
from utils.MLogger import MLogger

logger = MLogger(__name__)


class VmdBoneFrame():
    def __init__(self, fno=0, name=''):
        self.name = name
        self.bname = ''
        self.fno = fno
        self.position = MVector3D()
        self.rotation = MQuaternion()
        self.org_position = MVector3D()
        self.org_rotation = MQuaternion()
        self.interpolation = [20, 20, 0, 0, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 20, 20, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 20, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 0, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 0, 0] # noqa
        self.org_interpolation = [20, 20, 0, 0, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 20, 20, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 20, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 0, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107, 0, 0, 0] # noqa
        # 登録対象であるか否か
        self.key = False
        # VMD読み込み処理で読み込んだキーか
        self.read = False
        # 補間曲線の分割で追加したキーか
        self.split_interpolation = False

    def __str__(self):
        return "<VmdBoneFrame name:{0}, fno:{1}, position:{2}, rotation:{3}, euler:{4}, interpolation: {5}, key:{6}".format( \
            self.name, self.fno, self.position, self.rotation, self.rotation.toEulerAngles4MMD(), self.interpolation, self.key)

    def write(self, fout):
        if not self.bname:
            self.bname = self.name.encode('cp932').decode('shift_jis').encode('shift_jis')[:15].ljust(15, b'\x00')   # 15文字制限
        fout.write(self.bname)
        fout.write(struct.pack('<L', int(self.fno)))
        fout.write(struct.pack('<f', float(self.position.x())))
        fout.write(struct.pack('<f', float(self.position.y())))
        fout.write(struct.pack('<f', float(self.position.z())))
        v = self.rotation.toVector4D()
        fout.write(struct.pack('<f', float(v.x())))
        fout.write(struct.pack('<f', float(v.y())))
        fout.write(struct.pack('<f', float(v.z())))
        fout.write(struct.pack('<f', float(v.w())))
        fout.write(bytearray([int(min(127, max(0, x))) for x in self.interpolation]))


class VmdMorphFrame():
    def __init__(self, fno=0):
        self.name = ''
        self.bname = ''
        self.fno = fno
        self.ratio = 0
    
    def write(self, fout):
        if not self.bname:
            self.bname = self.name.encode('cp932').decode('shift_jis').encode('shift_jis')[:15].ljust(15, b'\x00')   # 15文字制限
        fout.write(self.bname)
        fout.write(struct.pack('<L', int(self.fno)))
        fout.write(struct.pack('<f', float(self.ratio)))

    def __str__(self):
        return "<VmdMorphFrame name:{0}, fno:{1}, ratio:{2}".format(self.name, self.fno, self.ratio)


class VmdCameraFrame():
    def __init__(self):
        self.fno = 0
        self.length = 0
        self.position = MVector3D(0, 0, 0)
        self.euler = MVector3D(0, 0, 0)
        self.interpolation = [20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107, 20, 107]
        self.angle = 0
        self.perspective = 0

    def write(self, fout):
        fout.write(struct.pack('<L', int(self.fno)))
        fout.write(struct.pack('<f', float(self.length)))
        fout.write(struct.pack('<f', float(self.position.x())))
        fout.write(struct.pack('<f', float(self.position.y())))
        fout.write(struct.pack('<f', float(self.position.z())))
        fout.write(struct.pack('<f', float(self.euler.x())))
        fout.write(struct.pack('<f', float(self.euler.y())))
        fout.write(struct.pack('<f', float(self.euler.z())))
        fout.write(bytearray([int(min(127, max(0, x))) for x in self.interpolation]))
        fout.write(struct.pack('<L', int(self.angle)))
        fout.write(struct.pack('b', self.perspective))


class VmdLightFrame():
    def __init__(self):
        self.fno = 0
        self.color = MVector3D(0, 0, 0)
        self.position = MVector3D(0, 0, 0)

    def write(self, fout):
        fout.write(struct.pack('<L', self.fno))
        fout.write(struct.pack('<f', self.color.x()))
        fout.write(struct.pack('<f', self.color.y()))
        fout.write(struct.pack('<f', self.color.z()))
        fout.write(struct.pack('<f', self.position.x()))
        fout.write(struct.pack('<f', self.position.y()))
        fout.write(struct.pack('<f', self.position.z()))


class VmdShadowFrame():
    def __init__(self):
        self.fno = 0
        self.type = 0
        self.distance = 0

    def write(self, fout):
        fout.write(struct.pack('<L', self.fno))
        fout.write(struct.pack('<f', self.type))
        fout.write(struct.pack('<f', self.distance))


# VmdShowIkFrame のikの中の要素
class VmdInfoIk():
    def __init__(self, name='', onoff=0):
        self.name = name
        self.onoff = onoff


class VmdShowIkFrame():
    def __init__(self):
        self.fno = 0
        self.show = 0
        self.ik_count = 0
        self.ik = []

    def write(self, fout):
        fout.write(struct.pack('<L', self.fno))
        fout.write(struct.pack('b', self.show))
        fout.write(struct.pack('<L', len(self.ik)))
        for k in (self.ik):
            fout.write(k.name)
            fout.write(bytearray([0 for i in range(len(k.name), 20)]))  # IKボーン名20Byteの残りを\0で埋める
            fout.write(struct.pack('b', k.onoff))
        

# https://blog.goo.ne.jp/torisu_tetosuki/e/bc9f1c4d597341b394bd02b64597499d
# https://w.atwiki.jp/kumiho_k/pages/15.html
class VmdMotion():
    def __init__(self):
        self.path = ''
        self.signature = ''
        self.model_name = ''
        self.last_motion_frame = 0
        self.motion_cnt = 0
        # ボーン名：VmdBoneFrameの辞書(key:ボーン名)
        self.bones = {}
        self.morph_cnt = 0
        # モーフ名：VmdMorphFrameの辞書(key:モーフ名)
        self.morphs = {}
        self.camera_cnt = 0
        # カメラ：VmdCameraFrameの配列
        self.cameras = {}
        self.light_cnt = 0
        # 照明：VmdLightFrameの配列
        self.lights = []
        self.shadow_cnt = 0
        # セルフ影：VmdShadowFrameの配列
        self.shadows = []
        self.ik_cnt = 0
        # モデル表示・IK on/off：VmdShowIkFrameの配列
        self.showiks = []
        # ハッシュ値
        self.digest = None
    
    def regist_full_bf(self, bone_name: str, is_rot: bool, is_mov: bool, is_full: bool):
        prev_sep_fno = 0
        registed_bfs = []   # 登録対象bfリスト
        fnos = self.get_bone_fnos(bone_name)
        if len(fnos) > 2:
            if is_full:
                for prev_fno, next_fno in zip(fnos[:-1], fnos[1:]):
                    # キーフレ間を全部埋める(そのまま登録すると、キーが変わるので、別保持)
                    for fno in range(prev_fno + 1, next_fno):
                        bf = self.calc_bf(bone_name, fno)
                        bf.key = True
                        registed_bfs.append(bf)
            else:
                start_fno = fnos[0]     # 開始フレーム番号
                fno = fnos[1]           # 次のフレーム番号
                prev_bf = self.calc_bf(bone_name, start_fno)    # 繋ぐ対象のbf
                fill_bfs = []
                while fno < fnos[-1]:
                    now_bf = self.calc_bf(bone_name, fno)           # 繋ぐ対象のbf
                    next_bf = self.calc_bf(bone_name, fno + 1)      # 繋ぐ先のbf

                    if not now_bf.read:
                        # 読み込みキーではない場合、結合を試す
                        
                        # 現在キーを追加
                        fill_bfs.append(now_bf)

                        if self.join_bf(prev_bf, fill_bfs, next_bf, is_rot, is_mov):
                            # 全ての補間曲線が繋ぐのに成功した場合、繋ぐ
                            logger.test("fno: %s, %s, ○補間曲線結合", fno, bone_name)

                            # nowキーは有効にしないでそのまま登録だけする
                            registed_bfs.append(now_bf)

                            # startはそのままで、nowだけ動かす
                            fno = fno + 1       # 現在フレームを次に移す
                        else:
                            logger.test("fno: %s, %s, ×補間曲線結合失敗", fno, bone_name)
                            # どれか失敗してたら、キーを有効にして残す

                            now_bf.key = True
                            registed_bfs.append(now_bf)

                            start_fno = fno     # 開始を現在フレーム
                            fill_bfs = []       # 中間キーをクリア
                            fno = fno + 1       # 現在フレームを次に移す
                    else:
                        # 読み込み時のキーである場合、既に登録されているのでスルー
                        start_fno = fno     # 開始を現在フレーム
                        fill_bfs = []       # 中間キーをクリア
                        fno = fno + 1       # 現在フレームを次に移す

                    if fno // 500 > prev_sep_fno:
                        logger.info("-- %sフレーム目完了", fno)
                        prev_sep_fno = fno // 500

            # 保持したのを登録しなおし
            for bf in registed_bfs:
                self.bones[bone_name][bf.fno] = bf

    # 指定ボーンの不要キーを削除する
    def remove_unnecessary_bf(self, bone_name: str, is_rot: bool, is_mov: bool):
        # キーフレ（全部）を取得する
        fnos = self.get_bone_fnos(bone_name)
        prev_sep_fno = 0
        if len(fnos) > 2:
            start_fno = fnos[0]     # 開始フレーム番号
            fno = fnos[1]           # 次のフレーム番号
            prev_bf = self.calc_bf(bone_name, start_fno)    # 繋ぐ対象のbf
            fill_bfs = []
            while fno < fnos[-1]:
                now_bf = self.calc_bf(bone_name, fno)           # 繋ぐ対象のbf
                next_bf = self.calc_bf(bone_name, fno + 1)      # 繋ぐ先のbf

                if not now_bf.read:
                    # 読み込みキーではない場合、結合を試す
                    
                    # 現在キーを追加
                    fill_bfs.append(now_bf)

                    if self.join_bf(prev_bf, fill_bfs, next_bf, is_rot, is_mov):
                        # 全ての補間曲線が繋ぐのに成功した場合、繋ぐ
                        logger.debug("fno: %s, %s, ○補間曲線結合", fno, bone_name)

                        # nowキーを物理的に削除する
                        if fno in self.bones[bone_name]:
                            del self.bones[bone_name][fno]

                        # startはそのままで、nowだけ動かす
                        fno = fno + 1       # 現在フレームを次に移す
                    else:
                        logger.debug("fno: %s, %s, ×補間曲線結合失敗", fno, bone_name)
                        # どれか失敗してたら、そのまま残す
                        start_fno = fno     # 開始を現在フレーム
                        fill_bfs = []       # 中間キーをクリア
                        fno = fno + 1       # 現在フレームを次に移す
                else:
                    # 読み込み時のキーである場合、強制的に残す
                    start_fno = fno     # 開始を現在フレーム
                    fill_bfs = []       # 中間キーをクリア
                    fno = fno + 1       # 現在フレームを次に移す

                if fno // 500 > prev_sep_fno:
                    logger.info("-- %sフレーム目完了", fno)
                    prev_sep_fno = fno // 500

    # 補間曲線込みでbfを結合できる場合、結合する
    def join_bf(self, prev_bf: VmdBoneFrame, fill_bfs: list, next_bf: VmdBoneFrame, is_rot: bool, is_mov: bool):
        rot_values = []

        if len(fill_bfs) > 0:
            # 中間がある場合

            # 回転の場合、クォータニオンのthetaを参照する
            rot_values.append(0)                                                    # 開始フレーム自体の変位はなし
            rot_values.append(prev_bf.rotation.calcTheata(fill_bfs[0].rotation))    # 最初の変位

            for before_bf, after_bf in zip(fill_bfs[:-1], fill_bfs[1:]):
                # 前後の変位を測定する
                rot_values.append(before_bf.rotation.calcTheata(after_bf.rotation))

            rot_values.append(fill_bfs[-1].rotation.calcTheata(next_bf.rotation))    # 最後の変位
        else:
            # 間がない場合
            rot_values = [prev_bf.rotation.calcTheata(next_bf.rotation)]    # 最初の変位

        # 結合したベジェ曲線
        joined_rot_bzs = MBezierUtils.join_value_2_bezier(rot_values) if is_rot else True

        if joined_rot_bzs:
            # 結合できた場合、補間曲線をnextに設定
            if is_rot:
                self.reset_interpolation_parts(prev_bf.name, next_bf, joined_rot_bzs, MBezierUtils.R_x1_idxs, MBezierUtils.R_y1_idxs, MBezierUtils.R_x2_idxs, MBezierUtils.R_y2_idxs)

            return True

        # 結合できなかった場合、False
        return False

    # 補間曲線分割ありで登録
    def regist_bf(self, bf: VmdBoneFrame, bone_name: str, fno: int):
        # 登録対象の場合のみ、補間曲線リセットで登録する
        regist_bf = self.calc_bf(bone_name, fno, is_reset_interpolation=True)
        regist_bf.position = bf.position
        regist_bf.rotation = bf.rotation
        # キーを登録
        regist_bf.key = True
        self.bones[bone_name][fno] = regist_bf
        # 補間曲線を設定（有効なキーのみ）
        prev_fno, next_fno = self.get_bone_prev_next_fno(bone_name, fno=fno, is_key=True)

        prev_bf = self.calc_bf(bone_name, prev_fno)
        next_bf = self.calc_bf(bone_name, next_fno)
        self.split_bf_by_fno(bone_name, prev_bf, next_bf, fno)

    # 補間曲線を考慮した指定フレーム番号の位置
    # https://www55.atwiki.jp/kumiho_k/pages/15.html
    # https://harigane.at.webry.info/201103/article_1.html
    def calc_bf(self, bone_name: str, fno: int, is_key=False, is_read=False, is_reset_interpolation=False):
        fill_bf = VmdBoneFrame(fno=fno, name=bone_name)

        if bone_name not in self.bones:
            self.bones[bone_name] = {fno: fill_bf}
            return fill_bf
        
        # 条件に合致するフレーム番号を探す
        # is_key: 登録対象のキーを探す
        # is_read: データ読み込み時のキーを探す
        fnos = [x for x in sorted(self.bones[bone_name].keys()) if (x == fno) and (not is_key or (is_key and self.bones[x].key)) and (not is_read or (is_read and self.bones[x].read))]
        
        if len(fnos) > 0:
            # 合致するキーが見つかった場合、それを返す
            return self.bones[bone_name][fnos[0]]
        else:
            # 合致するキーが見つからなかった場合
            if is_key or is_read:
                # 既存キーのみ探している場合はNone
                return None

        # 番号より前のフレーム番号
        before_fnos = [x for x in sorted(self.bones[bone_name].keys()) if (x < fno)]
        # 番号より後のフレーム番号
        after_fnos = [x for x in sorted(self.bones[bone_name].keys()) if (x > fno)]

        if len(after_fnos) == 0 and len(before_fnos) == 0:
            return fill_bf

        if len(after_fnos) == 0:
            # 番号より前があって、後のがない場合、前のをコピーして返す
            fill_bf = copy.deepcopy(self.bones[bone_name][before_fnos[-1]])
            fill_bf.fno = fno
            return fill_bf
        
        if len(before_fnos) == 0:
            # 番号より後があって、前がない場合、後のをコピーして返す
            fill_bf = copy.deepcopy(self.bones[bone_name][after_fnos[0]])
            fill_bf.fno = fno
            return fill_bf

        prev_bf = self.bones[bone_name][before_fnos[-1]]
        next_bf = self.bones[bone_name][after_fnos[0]]

        # 補間曲線を元に間を埋める
        fill_bf.rotation = self.calc_bf_rot(prev_bf, fill_bf, next_bf)
        fill_bf.position = self.calc_bf_pos(prev_bf, fill_bf, next_bf)

        if is_reset_interpolation:
            # 補間曲線再設定の場合、範囲外でも構わないので補間曲線を設定する

            # 回転の分割
            r_x, r_y, r_t, r_bresult, r_aresult, r_before_bz, r_after_bz \
                = MBezierUtils.split_bezier_mmd(next_bf.interpolation[MBezierUtils.R_x1_idxs[3]], next_bf.interpolation[MBezierUtils.R_y1_idxs[3]], \
                                                next_bf.interpolation[MBezierUtils.R_x2_idxs[3]], next_bf.interpolation[MBezierUtils.R_y2_idxs[3]], \
                                                prev_bf.fno, fill_bf.fno, next_bf.fno)
            # 移動Xの分割
            x_x, x_y, x_t, x_bresult, x_aresult, x_before_bz, x_aftex_bz \
                = MBezierUtils.split_bezier_mmd(next_bf.interpolation[MBezierUtils.MX_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MX_y1_idxs[3]], \
                                                next_bf.interpolation[MBezierUtils.MX_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MX_y2_idxs[3]], \
                                                prev_bf.fno, fill_bf.fno, next_bf.fno)
            # 移動Yの分割
            y_x, y_y, y_t, y_bresult, y_aresult, y_before_bz, y_aftey_bz \
                = MBezierUtils.split_bezier_mmd(next_bf.interpolation[MBezierUtils.MY_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MY_y1_idxs[3]], \
                                                next_bf.interpolation[MBezierUtils.MY_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MY_y2_idxs[3]], \
                                                prev_bf.fno, fill_bf.fno, next_bf.fno)
            # 移動Zの分割
            z_x, z_y, z_t, z_bresult, z_aresult, z_before_bz, z_aftez_bz \
                = MBezierUtils.split_bezier_mmd(next_bf.interpolation[MBezierUtils.MZ_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MZ_y1_idxs[3]], \
                                                next_bf.interpolation[MBezierUtils.MZ_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MZ_y2_idxs[3]], \
                                                prev_bf.fno, fill_bf.fno, next_bf.fno)

            # 強制設定
            self.reset_interpolation(bone_name, prev_bf, fill_bf, next_bf, r_before_bz, r_after_bz, \
                                     MBezierUtils.R_x1_idxs, MBezierUtils.R_y1_idxs, MBezierUtils.R_x2_idxs, MBezierUtils.R_y2_idxs)
            self.reset_interpolation(bone_name, prev_bf, fill_bf, next_bf, x_before_bz, x_aftex_bz, \
                                     MBezierUtils.MX_x1_idxs, MBezierUtils.MX_y1_idxs, MBezierUtils.MX_x2_idxs, MBezierUtils.MX_y2_idxs)
            self.reset_interpolation(bone_name, prev_bf, fill_bf, next_bf, y_before_bz, y_aftey_bz, \
                                     MBezierUtils.MY_x1_idxs, MBezierUtils.MY_y1_idxs, MBezierUtils.MY_x2_idxs, MBezierUtils.MY_y2_idxs)
            self.reset_interpolation(bone_name, prev_bf, fill_bf, next_bf, z_before_bz, z_aftez_bz, \
                                     MBezierUtils.MZ_x1_idxs, MBezierUtils.MZ_y1_idxs, MBezierUtils.MZ_x2_idxs, MBezierUtils.MZ_y2_idxs)

        return fill_bf

    # 補間曲線を元に、回転ボーンの値を求める
    def calc_bf_rot(self, prev_bf: VmdBoneFrame, fill_bf: VmdBoneFrame, next_bf: VmdBoneFrame):
        if prev_bf.rotation != next_bf.rotation:
            # 回転補間曲線
            rx, ry, rt = MBezierUtils.evaluate(next_bf.interpolation[MBezierUtils.R_x1_idxs[3]], next_bf.interpolation[MBezierUtils.R_y1_idxs[3]], \
                                               next_bf.interpolation[MBezierUtils.R_x2_idxs[3]], next_bf.interpolation[MBezierUtils.R_y2_idxs[3]], \
                                               prev_bf.fno, fill_bf.fno, next_bf.fno)
            return MQuaternion.slerp(prev_bf.rotation, next_bf.rotation, ry)

        return copy.deepcopy(prev_bf.rotation)

    # 補間曲線を元に移動ボーンの値を求める
    def calc_bf_pos(self, prev_bf: VmdBoneFrame, fill_bf: VmdBoneFrame, next_bf: VmdBoneFrame):

        # 補間曲線を元に間を埋める
        if prev_bf.position != next_bf.position:
            # http://rantyen.blog.fc2.com/blog-entry-65.html
            # X移動補間曲線
            xx, xy, xt = MBezierUtils.evaluate(next_bf.interpolation[MBezierUtils.MX_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MX_y1_idxs[3]], \
                                               next_bf.interpolation[MBezierUtils.MX_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MX_y2_idxs[3]], \
                                               prev_bf.fno, fill_bf.fno, next_bf.fno)
            # Y移動補間曲線
            yx, yy, yt = MBezierUtils.evaluate(next_bf.interpolation[MBezierUtils.MY_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MY_y1_idxs[3]], \
                                               next_bf.interpolation[MBezierUtils.MY_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MY_y2_idxs[3]], \
                                               prev_bf.fno, fill_bf.fno, next_bf.fno)
            # Z移動補間曲線
            zx, zy, zt = MBezierUtils.evaluate(next_bf.interpolation[MBezierUtils.MZ_x1_idxs[3]], next_bf.interpolation[MBezierUtils.MZ_y1_idxs[3]], \
                                               next_bf.interpolation[MBezierUtils.MZ_x2_idxs[3]], next_bf.interpolation[MBezierUtils.MZ_y2_idxs[3]], \
                                               prev_bf.fno, fill_bf.fno, next_bf.fno)

            fill_pos = MVector3D()
            fill_pos.setX(prev_bf.position.x() + ((next_bf.position.x() - prev_bf.position.x()) * xy))
            fill_pos.setY(prev_bf.position.y() + ((next_bf.position.y() - prev_bf.position.y()) * yy))
            fill_pos.setZ(prev_bf.position.z() + ((next_bf.position.z() - prev_bf.position.z()) * zy))
            
            return fill_pos
        
        return copy.deepcopy(prev_bf.position)
    
    # キーフレを指定されたフレーム番号の前後で分割する
    def split_bf_by_fno(self, target_bone_name: str, prev_bf: VmdBoneFrame, next_bf: VmdBoneFrame, fill_fno: int):
        if not (prev_bf.fno < fill_fno < next_bf.fno):
            # 間の分割が出来ない場合、終了
            return False

        # 補間曲線もともに分割する
        fill_bf = self.calc_bf(target_bone_name, fill_fno, is_reset_interpolation=True)
        fill_bf.key = True
        self.bones[target_bone_name][fill_fno] = fill_bf

        # 分割結果
        fill_result = True
        # 前半の分割
        fill_result = self.split_bf(target_bone_name, prev_bf, fill_bf) and fill_result
        # 後半の分割
        fill_result = self.split_bf(target_bone_name, fill_bf, next_bf) and fill_result

        return fill_result

    # キーフレを移動量の中心で分割する
    def split_bf(self, target_bone_name: str, prev_bf: VmdBoneFrame, next_bf: VmdBoneFrame):
        if prev_bf.fno == next_bf.fno:
            # 間の分割が出来ない場合、終了
            return True

        # 回転中点fno
        r_fill_fno = self.get_split_fill_fno(target_bone_name, prev_bf, next_bf, \
                                             MBezierUtils.R_x1_idxs, MBezierUtils.R_y1_idxs, MBezierUtils.R_x2_idxs, MBezierUtils.R_y2_idxs)
        # 移動X中点fno
        x_fill_fno = self.get_split_fill_fno(target_bone_name, prev_bf, next_bf, \
                                             MBezierUtils.MX_x1_idxs, MBezierUtils.MX_y1_idxs, MBezierUtils.MX_x2_idxs, MBezierUtils.MX_y2_idxs)
        # 移動Y中点fno
        y_fill_fno = self.get_split_fill_fno(target_bone_name, prev_bf, next_bf, \
                                             MBezierUtils.MY_x1_idxs, MBezierUtils.MY_y1_idxs, MBezierUtils.MY_x2_idxs, MBezierUtils.MY_y2_idxs)
        # 移動Z中点fno
        z_fill_fno = self.get_split_fill_fno(target_bone_name, prev_bf, next_bf, \
                                             MBezierUtils.MZ_x1_idxs, MBezierUtils.MZ_y1_idxs, MBezierUtils.MZ_x2_idxs, MBezierUtils.MZ_y2_idxs)

        fnos = []
        for fill_fno in [r_fill_fno, x_fill_fno, y_fill_fno, z_fill_fno]:
            if fill_fno and prev_bf.fno < fill_fno < next_bf.fno:
                # fnoがあって範囲内の場合、設定対象でfnoを保持
                fnos.append(fill_fno)

        # 重複なしの昇順リスト
        fnos = list(sorted(list(set(fnos))))

        fill_result = True
        if len(fnos) > 0:
            # 現在処理対象以外にfnoがある場合、その最小地点で前後に分割
            fill_result = self.split_bf_by_fno(target_bone_name, prev_bf, next_bf, fnos[0]) and fill_result
        
        return fill_result
    
    # キーフレを指定bf間の中間で区切れるフレーム番号を取得する
    # 分割が不要（範囲内に収まってる）場合、-1で対象外
    def get_split_fill_fno(self, target_bone_name: str, prev_bf: VmdBoneFrame, next_bf: VmdBoneFrame, \
                           x1_idxs: list, y1_idxs: list, x2_idxs: list, y2_idxs: list):
        next_x1v = next_bf.interpolation[x1_idxs[3]]
        next_y1v = next_bf.interpolation[y1_idxs[3]]
        next_x2v = next_bf.interpolation[x2_idxs[3]]
        next_y2v = next_bf.interpolation[y2_idxs[3]]

        if not MBezierUtils.is_fit_bezier_mmd([MVector2D(), MVector2D(next_x1v, next_y1v), MVector2D(next_x2v, next_y2v), MVector2D()]):
            # ベジェ曲線がMMDの範囲内に収まっていない場合、中点で分割
            new_fill_fno, _, _ = MBezierUtils.evaluate_by_t(next_x1v, next_y1v, next_x2v, next_y2v, prev_bf.fno, next_bf.fno, 0.5)

            if prev_bf.fno < new_fill_fno < next_bf.fno:
                return new_fill_fno
        
        # 範囲内でない場合
        return -1

    # 補間曲線の再設定処理
    def reset_interpolation(self, target_bone_name: str, prev_bf: VmdBoneFrame, now_bf: VmdBoneFrame, next_bf: VmdBoneFrame, \
                            before_bz: list, after_bz: list, x1_idxs: list, y1_idxs: list, x2_idxs: list, y2_idxs: list):
        
        # 今回キーに設定
        self.reset_interpolation_parts(target_bone_name, now_bf, before_bz, x1_idxs, y1_idxs, x2_idxs, y2_idxs)

        # nextキーに設定
        self.reset_interpolation_parts(target_bone_name, next_bf, after_bz, x1_idxs, y1_idxs, x2_idxs, y2_idxs)

    # 補間曲線の再設定部品
    def reset_interpolation_parts(self, target_bone_name: str, bf: VmdBoneFrame, bzs: list, x1_idxs: list, y1_idxs: list, x2_idxs: list, y2_idxs: list):
        # キーの始点は、B
        bf.interpolation[x1_idxs[0]] = bf.interpolation[x1_idxs[1]] = bf.interpolation[x1_idxs[2]] = bf.interpolation[x1_idxs[3]] = int(bzs[1].x())
        bf.interpolation[y1_idxs[0]] = bf.interpolation[y1_idxs[1]] = bf.interpolation[y1_idxs[2]] = bf.interpolation[y1_idxs[3]] = int(bzs[1].y())

        # キーの終点は、C
        bf.interpolation[x2_idxs[0]] = bf.interpolation[x2_idxs[1]] = bf.interpolation[x2_idxs[2]] = bf.interpolation[x2_idxs[3]] = int(bzs[2].x())
        bf.interpolation[y2_idxs[0]] = bf.interpolation[y2_idxs[1]] = bf.interpolation[y2_idxs[2]] = bf.interpolation[y2_idxs[3]] = int(bzs[2].y())

    # ボーンモーション：フレーム番号リスト
    def get_bone_fnos(self, *bone_names, **kwargs):
        if not self.bones or self.motion_cnt == 0:
            return []
        
        # is_key: 登録対象のキーを探す
        # is_read: データ読み込み時のキーを探す
        is_key = True if "is_key" in kwargs and kwargs["is_key"] else False
        is_read = True if "is_read" in kwargs and kwargs["is_read"] else False
        
        # 条件に合致するフレーム番号を探す
        keys = []
        for bone_name in bone_names:
            if bone_name in self.bones:
                keys.extend([x for x in self.bones[bone_name].keys() if (not is_key or (is_key and self.bones[bone_name][x].key)) and (not is_read or (is_read and self.bones[bone_name][x].read))])
        
        # 重複を除いた昇順フレーム番号リストを返す
        return sorted(list(set(keys)))
    
    # 指定されたfnoの前後のキーを取得する
    def get_bone_prev_next_fno(self, *bone_names, **kwargs):
        # 指定されたボーン名のfnos
        fnos = self.get_bone_fnos(*bone_names, **kwargs)

        fno = kwargs["fno"] if "fno" in kwargs else 0

        # 指定より前のキーフレ
        prev_fnos = [x for x in fnos if x < fno]
        # 指定より後のキーフレ
        next_fnos = [x for x in fnos if x > fno]
        
        # 前のは取れなければ-1で強制的に前の
        prev_fno = -1 if len(prev_fnos) <= 0 else prev_fnos[-1]
        # 後のは取れなければ最終フレーム＋1
        next_fno = self.last_motion_frame + 1 if len(next_fnos) <= 0 else next_fnos[0]

        return prev_fno, next_fno

    # モーフモーション：フレーム番号リスト
    def get_morph_fnos(self, morph_name: str):
        if not self.morphs or self.morph_cnt == 0 or morph_name not in self.morphs:
            return []
        
        return sorted([fno for fno in self.morphs[morph_name].keys()])

    # カメラモーション：フレーム番号リスト
    def get_camera_fnos(self):
        if not self.cameras or self.camera_cnt == 0:
            return []
        
        return sorted([fno for fno in self.cameras.keys()])
        
    # ボーンモーション：一次元配列
    def get_bone_frames(self):
        total_bone_frames = []

        for bone_name, bone_frames in self.bones.items():
            if bone_name not in ["SIZING_ROOT_BONE", "頭頂", "右つま先実体", "左つま先実体", "右足底辺", "左足底辺"]:
                # サイジング用ボーンは出力しない
                fnos = self.get_bone_fnos(bone_name)
                
                if len(fnos) > 0:
                    # 各ボーンの最終キーだけ先に登録
                    total_bone_frames.append(bone_frames[fnos[-1]])
        
        for bone_name, bone_frames in self.bones.items():
            if bone_name not in ["SIZING_ROOT_BONE", "頭頂", "右つま先実体", "左つま先実体", "右足底辺", "左足底辺"]:
                # サイジング用ボーンは出力しない
                fnos = self.get_bone_fnos(bone_name)

                if len(fnos) > 1:
                    # キーフレを最後の一つ手前まで登録
                    for fno in fnos[:-1]:
                        if bone_frames[fno].key:
                            total_bone_frames.append(bone_frames[fno])
        
        return total_bone_frames
    
    # モーフモーション：一次元配列
    def get_morph_frames(self):
        total_morph_frames = []

        for morph_name, morph_frames in self.morphs.items():
            fnos = self.get_morph_fnos(morph_name)
            
            if len(fnos) > 0:
                # 各モーフの最終キーだけ先に登録
                total_morph_frames.append(morph_frames[fnos[-1]])
        
        for morph_name, morph_frames in self.morphs.items():
            fnos = self.get_morph_fnos(morph_name)

            if len(fnos) > 1:
                # キーフレを最後の一つ手前まで登録
                for fno in fnos[:-1]:
                    total_morph_frames.append(morph_frames[fno])
        
        return total_morph_frames

    # カメラモーション：一次元配列
    def get_camera_frames(self):
        total_camera_frames = []

        # カメラキーフレを逆順に登録
        for fno in reversed(self.get_camera_fnos()):
            total_camera_frames.append(self.cameras[fno])

        return total_camera_frames

    # ボーンキーフレを追加
    def append_bone_frame(self, frame: VmdBoneFrame):
        if frame.name not in self.bones:
            # まだ該当ボーン名がない場合、追加
            self.bones[frame.name] = {}
        
        self.bones[frame.name][frame.fno] = frame

    # モーフキーフレを追加
    def append_morph_frame(self, frame: VmdMorphFrame):
        if frame.name not in self.morphs:
            # まだ該当モーフ名がない場合、追加
            self.morphs[frame.name] = {}
        
        self.morphs[frame.name][frame.fno] = frame



