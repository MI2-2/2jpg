# -*- coding:utf-8 -*-
# png, avifをjpgに一括変換
#

import os, sys, shutil, subprocess, tempfile, re, unicodedata, configparser
from concurrent import futures
from PIL import Image   # pillow インストール必要
import pillow_avif      # pillow-avif-plugin インストール必要
from send2trash import send2trash # send2trash インストール必要
from winsort import winsort # 自作モジュール必要

# 設定の読み込み
inipath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '2jpg.ini')
ini = configparser.ConfigParser()
if os.path.isfile(inipath):
    ini.read(inipath, 'UTF-8')
    # 7zipの場所
    z7 = ini['global']['7zpass']
    if not os.path.isfile(z7):
        print('7zipがありません')
        sys.exit()
    ext = ini['global']['ExcludeFile']


# png -> jpg 変換関数
def png_conv(p):
    if os.path.splitext(p)[1] == '.png' or os.path.splitext(p)[1] == '.avif':
        with Image.open(os.path.join(tpath, os.path.basename(p))) as conv_image:
            conv_image = conv_image.convert('RGB')
            conv_image.save(os.path.join(new_img_path, os.path.splitext(os.path.basename(p))[0] + '.jpg'))
    else:
        shutil.move(os.path.join(tpath, os.path.basename(p)), new_img_path)


if __name__ == '__main__':

    # 処理ファイル名を引数から受け取り
    files = sys.argv

    for file in files[1:]:

        print(os.path.basename(file) + ' 処理中')

        # 作業用一時フォルダの作成
        with tempfile.TemporaryDirectory() as tempdir:

            # 処理対象がファイルのときの処理
            if os.path.isfile(file):

            # ファイル名、パス名の定義
                fname = os.path.splitext(os.path.basename(file))[0]     # 元ファイル名、拡張子なし
                path = os.path.dirname(file)                            # 元ファイルのあるフォルダ名
                ppath = os.path.join(path, fname)                       # 新しいフォルダ名
                tpath = os.path.join(tempdir, fname)                    # 作業用一時フォルダ名

                # 解凍先フォルダの作成
                if not os.path.isdir(tpath):
                    os.makedirs(tpath)

                # 7zipで書庫展開(フォルダ構造なし、フラット展開)
                print('書庫展開中')
                subprocess.run([z7, 'e', file, '-y', '-bd', '-o' + tpath], stdout=subprocess.DEVNULL)
                # フォルダーを検索
                list_dirs = next(os.walk(tpath))[1]
                # サブフォルダが複数あったらエラー
                if len(list_dirs) > 1:
                    print('フォルダが二重もしくは複数あります')
                    print('処理方法を見直してください')
                    input()
                    continue
                # サブフォルダが1つならそのフォルダー名を新規ファイル名として採用
                elif len(list_dirs) == 1:
                    fname = list_dirs[0]

            # 処理対象がフォルダのときの処理
            elif os.path.isdir(file):

                # ファイル名、パス名の定義
                fname = os.path.basename(file)                          # 元フォルダ名
                path = os.path.dirname(file)                            # 元ファイルのあるフォルダ名
                ppath = file                                            # 新しいフォルダ名
                tpath = os.path.join(tempdir, fname)                    # 作業用一時フォルダ名

                # 一時作業フォルダに全ファイルをコピー
                os.mkdir(tpath)
                pic_files = os.listdir(file)
                for pic_file in pic_files:
                    shutil.copy(os.path.join(file, pic_file), tpath)

            # これ以降ファイル、フォルダ共通処理

            for curdir, dirs, files in os.walk(tpath):
                for f in files:
                    # 不要ファイルの削除
                    if re.search(ext, f):
                        os.remove(os.path.join(curdir, f))
                        print(f + ' を削除しました。')
                    # coverファイルのリネーム
                    if 'cover' in f:
                        os.rename(os.path.join(tpath, f), os.path.join(tpath, '00000' + os.path.splitext(f)[1]))

            # 一時フォルダのファイルリスト
            all_pics = next(os.walk(tpath))[2]

            # 自然順ソート
            all_pics = winsort(all_pics)

            # 変換画像を保存するフォルダ
            new_img_path = os.path.join(tpath, 'trim', 'pics')

            #もし存在しなければ作る
            if not os.path.isdir(new_img_path):
                os.makedirs(new_img_path)

            print('画像変換中...')
            with futures.ThreadPoolExecutor() as executor:
                result = executor.map(png_conv, all_pics)

            # フォルダ削除、trimフォルダリネーム
            if os.path.isdir(os.path.join(tpath, 'trim', fname)):
                shutil.rmtree(os.path.join(tpath, 'trim', fname))
            os.rename(new_img_path, (os.path.join(tpath, 'trim', fname)))
            # MangaRoo の AVIF フォルダ対策
            if '[AVIF]' in fname:
                m = re.match(r'\[\d{8}\]\[一般コミック\]\[(.*?)\] (.*) \[.*?\]\[AVIF\]\[DL版\]', fname)
                m1 = m.group(1).replace(' ', '×')
                new_fname = '[' + m1 + '] ' + m.group(2)
                os.rename(os.path.join(tpath, 'trim', fname), os.path.join(tpath, 'trim', new_fname))
                fname = new_fname

            # 元ファイルはゴミ箱に
            if os.path.isfile(file):
                send2trash(file)

            # zip書庫に圧縮
            print('書庫作成中...')
            zip_dir = os.path.join(tpath, 'trim', fname)
            subprocess.run([z7, 'a', '-tzip', os.path.join(path, fname) + '.zip', zip_dir], stdout=subprocess.DEVNULL)
            
            new_name = fname
            new_name = '(一般コミック) ' + new_name
            # 文字列の正規化
            new_name = unicodedata.normalize('NFKC', new_name)
            # 文字列の置換
            new_name = re.sub(r'\[[^\]]*\]', lambda m: m[0].replace('x', '×'), new_name)
            new_name = new_name.replace('_', ' ').replace('!', '！').replace(':', '：').replace('/', '／').replace('?', '？').replace('~', '～').replace('卷', '巻')

            if not os.path.isfile(os.path.join(path, new_name + '.zip')):
                os.rename(os.path.join(path, fname + '.zip'), os.path.join(path, new_name + '.zip'))
            else:
                pass

        if os.path.isdir(file):
            try:
                send2trash(file)
            except Exception:
                shutil.rmtree(file, ignore_errors=True)
        print('')

    else:
        print('処理終了')
        sys.exit()