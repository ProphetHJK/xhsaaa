import checkdownbase
import logging
import json
import time
import requests
import os
import random
import subprocess
from datetime import datetime

from pymediainfo import MediaInfo
from requests.adapters import HTTPAdapter
from pathlib import Path
import re
import shutil


class CheckXhsDown(checkdownbase.CheckDown):
    def __init__(self, conn):
        super().__init__(conn)
        self.proxy = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        self.videodownlist = []
        self.session.proxies = {}
        self.errorpushflag = 0
        self.checktype = 0
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}
        self.session.headers = headers
        # 专用于下载的session，没有认证信息
        self.downsession = requests.Session()
        self.downsession.headers = headers
        self.downsession.mount('http://', HTTPAdapter(max_retries=5))
        self.downsession.mount('https://', HTTPAdapter(max_retries=5))
        self.downsession.proxies = {}
        self.img_path = "xhsdown/download/pic"
        self.video_path = "xhsdown/download/vid"
        
    def check(self):
        super().check()
        if not os.path.exists(self.img_path):
            os.makedirs(self.img_path)
        if not os.path.exists(self.video_path):
            os.makedirs(self.video_path)

    def download(self):
        super().download()
        for videoinfo in self.videodownlist:
            self.real_img_path = os.path.join(self.img_path,videoinfo['folder'])
            self.real_video_path = os.path.join(self.video_path,videoinfo['folder'])

            title2 = videoinfo['title']
            if videoinfo['category'] != '':
                title2 = videoinfo['category'] + '#' + title2

            filename = videoinfo['upname'] + '-' + title2 + '-' + videoinfo['aid']
            filename = self.filtern(filename)
            mediatype = 0
            if videoinfo['downtype'] == 'pic':
                mediatype = 1
                ret = self.downpic(videoinfo['url'], self.real_img_path,
                              filename+'-pic{}'.format(videoinfo['number'])+'.jpg')
                if ret is None:
                    logging.info('下载图片失败')
                    continue
            elif videoinfo['downtype'] == 'vid':
                mediatype = 2
                videofilename = filename+'-'+videoinfo['quality']+'#'+str(videoinfo['bitrate'])
                fileabspath = os.path.join(self.real_video_path,videofilename+'.mp4')
                if os.path.exists(fileabspath):
                    logging.info('文件已存在，跳过，%s' % fileabspath)
                    # continue
                else:
                    # 预览图
                    ret2 = self.downvideo(videoinfo['url'], self.real_video_path,videofilename+'.mp4.tmp')
                    if ret2 is None:
                        logging.info('下载视频失败，aid:{},mid:{}'.format(videoinfo['aid'],videoinfo['mid']))
                        continue
                    ret1 = self.downpic(videoinfo['thumburl'], self.real_video_path,videofilename+'.jpg')
                    if ret1 is None:
                        logging.info('下载预览图失败')
                        continue
                    self.writeMediaData(videoinfo, self.real_video_path, fileabspath+'.tmp', fileabspath)
                    if os.path.exists(fileabspath):
                        os.remove(fileabspath + '.tmp')
                        logging.info('写入metadata成功')
                    else:
                        logging.info('写入metadata失败')
                        continue
            else:
                logging.info('unknown downtype:{}'.format(videoinfo['downtype']))
                continue
            nowtime = int(time.time())
            if videoinfo['quality'] == 'FHD':
                quality = 3
            elif videoinfo['quality'] == 'HD' or videoinfo['quality'] == 'HDP':
                quality = 2
            elif videoinfo['quality'] == 'SD':
                quality = 1
            else:
                quality = 0
            if videoinfo['updateflag'] == 0:
                self.conncursor.execute(
                    "insert or ignore into xhsdownlist(aid,type,quality,bitrate,time) values(?,?,?,?,?)", (videoinfo['aid'],mediatype,quality,int(videoinfo['bitrate']), nowtime))
            elif videoinfo['updateflag'] == 1:
                self.conncursor.execute(
                    "update xhsdownlist set quality=?,bitrate=?,time=? where aid=? and type=?", (quality,int(videoinfo['bitrate']),nowtime,videoinfo['aid'],mediatype))
            else:
                logging.info('未定义updateflag:{}'.format(videoinfo['updateflag']))
                continue

            self.conn.commit()
            logging.info('写入数据库成功')

    def jsonLoad(self, datalistjson,forcedown=False):
        for data in datalistjson:
            model_type = data.get('model_type')
            if model_type is not None:
                if model_type != 'note':
                    logging.info('model_type is not note:%s' % model_type)
                    continue

            id = data.get('id')
            cursor = self.conncursor.execute(
                "SELECT count(1) from xhsdownlist where aid=? and type=1", (id,))
            for row in cursor:
                count = row[0]
            if count > 0:
                # logging.info('this note is already download')
                continue
            type = data.get('type')
            timestamp = data.get('timestamp')
            if timestamp is None:
                timestamp = int(time.time())
            title = data.get('title')
            desc = data.get('desc')
            imageurllist = []
            images_list = data.get('images_list')

            try:
                category_name = data.get('recommend').get('category_name')
            except Exception as ex:
                category_name = None

            username = data.get('user').get('nickname')
            userid = data.get('user').get('userid')

            if images_list is not None:
                for image in images_list:
                    imageurl = image.get('original')
                    if imageurl == '':
                        imageurl = image.get('url_size_large')
                    imageurllist.append(imageurl)

            time_local = time.localtime(int(timestamp))
            dt = time.strftime("%Y%m%d_%H%M%S", time_local)

            if category_name is None:
                category_name = ''
            
            if self.checktype == 1:
                followed = data.get('user').get('followed')
                folder = '收藏'
            elif self.checktype == 2:
                folder = username+'#'+userid

            if type == 'normal':
                tempnum = 1
                for imageurl in imageurllist:
                    imginfo = {'aid': id, 'mid': userid, 'upname': username, 'desc': desc,
                                 'title': title, 'url': imageurl,'quality': 'HD',
                                 'bitrate': 0, 'duration': '', 'timestamp': timestamp, 
                                 'number': tempnum, 'category': category_name,'folder': folder,
                                 'updateflag': 0,'downtype': 'pic'}
                    self.videodownlist.append(imginfo)
                    tempnum = tempnum + 1

            elif type == 'video':
                try:
                    video_h264_list = data.get('video_info_v2').get(
                        'media').get('stream').get('h264')
                    video_h265_list = data.get('video_info_v2').get(
                        'media').get('stream').get('h265')
                    thumbpic = data.get('video_info_v2').get(
                        'image').get('thumbnail')
                except Exception as ex:
                    print(ex)
                    continue
                if video_h265_list is None:
                    continue
                # logging.info("{}:{}".format(id,video_h265_list))
                max_bitrate = 0
                if len(video_h265_list) == 0:
                    for video_h264 in video_h264_list:
                        video_bitrate = int(video_h264.get('video_bitrate'))
                        if video_bitrate > max_bitrate:
                            best_video = video_h264
                            max_bitrate = video_bitrate
                else:
                    for video_h265 in video_h265_list:
                        video_bitrate = int(video_h265.get('video_bitrate'))
                        if video_bitrate > max_bitrate:
                            best_video = video_h265
                            max_bitrate = video_bitrate
                if best_video is not None:
                    quality_type = best_video.get('quality_type')
                    master_url = best_video.get('master_url')
                    if quality_type == 'FHD':
                        quality = 3
                    elif quality_type == 'HD' or quality_type == 'HDP':
                        quality = 2
                    elif quality_type == 'SD':
                        quality = 1
                    else:
                        quality = 0
                    updateflag = 0
                    cursor = self.conncursor.execute(
                        "SELECT count(1) from xhsdownlist where aid=? and type=2", (id,))
                    for row in cursor:
                        count = row[0]
                    if count > 0:
                        updateflag = 1
                    # 如果已经下载过
                    if updateflag != 0:
                        cursor = self.conncursor.execute(
                            "SELECT count(1) from xhsdownlist where aid=? and type=2 and quality>=? and bitrate>=?", (id,quality,max_bitrate,))
                        for row in cursor:
                            count = row[0]
                        # 如果数据库中已是最好画质,跳过
                        if count > 0:
                            continue
                        else:
                            logging.info('better quality update,aid:{},mid:{},quality:{},bitrate:{}'.format(id,userid,quality_type,max_bitrate))
                    videoinfo = {'aid': id, 'mid': userid, 'upname': username, 'desc': desc,
                                 'title': title, 'url': master_url, 'thumburl': imageurllist[0], 'quality': quality_type,
                                 'bitrate': max_bitrate, 'duration': '', 'timestamp': timestamp, 'category': category_name,
                                 'folder': folder,'updateflag': updateflag,'downtype': 'vid'}
                    self.videodownlist.append(videoinfo)

    def filter(self):
        logging.info('start filter')

    def downpic(self,url,filepath, filename):
        r = self.downsession.get(url)
        if r.status_code != 200:
            logging.info("result error")
            return None
        img = r.content
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        path = os.path.join(filepath, filename)
        logging.info('start download pic:%s' % filename)
        if os.path.exists(path):
            logging.info('file exists')
        else:
            with open(path, 'wb') as f:
                f.write(img)
        return 0

    def downvideo(self,url, savePath, fileName):
        prog_text = '正在下载: {},url:{}'.format(fileName, url) + ' ...{}'
        filePath = os.path.join(savePath, fileName)
        logging.info('开始下载：%s' % filePath)
        if not os.path.exists(savePath):
            os.makedirs(savePath)
        if os.path.exists(filePath):
            logging.info(prog_text.format('文件已存在，重新下载'))
            os.remove(filePath)
        logging.info(prog_text.format('0%'))
        response = self.downsession.get(
            url, stream=True, headers={}, cookies={})
        if response.status_code != 200:
            logging.info("down fail: %d" % response.status_code)
            logging.info(response.text)
            return None
        dl_size = 0
        content_size = 0
        tmp_process = 0
        last_process = 0
        if 'content-length' in response.headers:
            content_size = int(response.headers['content-length'])
        elif 'Content-Length' in response.headers:
            content_size = int(response.headers['Content-Length'])
        with open(filePath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 2):
                f.write(chunk)
                if content_size:
                    dl_size += len(chunk)
                    tmp_process = int(round(dl_size / content_size, 2) * 100)
                    if tmp_process != last_process:
                        last_process = tmp_process
                        if tmp_process % 20 == 0:
                            prog = '{}%'.format(tmp_process)
                            logging.info(prog_text.format(prog))

        logging.info(prog_text.format('下载完成'))
        time.sleep(1)
        return 0
    
    def writeMediaData(self,videoinfo,metadataPath,inputfile,outputfile):
        metadatapath = os.path.join(metadataPath, "metadata.txt")
        time_local = time.localtime(int(videoinfo['timestamp']))
        dt = time.strftime("%Y-%m-%d", time_local)
        if os.path.exists(metadatapath):
            os.remove(metadatapath)
        logging.info("生成metadata")
        with open(metadatapath, 'w', encoding='utf8', newline='\n') as te:
            te.write(';FFMETADATA1\n')
            te.write("title={}\n".format(videoinfo['title']))  # 标题
            te.write("comment={}\n".format(videoinfo['desc'].replace('\n', '\\\n')))  # 简介
            te.write("album={}\n".format(videoinfo['title']))  # 专辑，等于title
            te.write("artist={}\n".format(videoinfo['upname']))  # 作者
            te.write("album_artist={}\n".format(str(videoinfo['mid'])))  # 专辑作者，等于作者
            te.write("episode_id={}\n".format(videoinfo['aid']))  # id号
            te.write("date={}\n".format(dt))  # "%Y-%m-%d"
            te.write("description={}\n".format(''))  # 介绍，一般没用
            te.write("genre={}\n".format(videoinfo['category']))  # 标签，最后没逗号

        ml = 'ffmpeg -i "{}" -i "{}" -map_metadata 1 -c copy "{}"'.format(
            inputfile, metadatapath, outputfile)
        ret = os.system(ml)
        if ret == 0:
            logging.info("写入metadata成功")
        else:
            logging.info("写入metadata失败")

    # 去重，删除低画质的
    def deduplication(self):
        logging.info('去重开始，目录：{}'.format(self.video_path))
        path = Path(self.video_path)
        cursor = self.conncursor.execute(
            "SELECT aid from xhsdownlist where type=2 order by time DESC")
        for row in cursor:
            aid = row[0]
            filelist = path.glob('**/*{}*.mp4'.format(aid))
            filenamelist = []
            for file in filelist:
                filename = os.path.splitext(file)[0]
                filenamelist.append(filename)
            if len(filenamelist) == 1:
                continue
            elif len(filenamelist) == 0:
                logging.info('[ERROR] no file exists,aid:{}'.format(aid))
                continue
            logging.info('more than one file,{},{}'.format(len(filenamelist),filenamelist))
            bestfileindex = 100
            max_quality = 0
            max_bitrate = 0
            for index in range(0,len(filenamelist)):
                r  = re.match(".*-([A-Z]*)#([0-9]*)$",filenamelist[index])
                if r is not None:
                    # print(r.group(1))
                    quality_type = r.group(1)
                    bitrate = r.group(2)
                    bitrate = int(bitrate)
                    if quality_type == 'FHD':
                        quality = 3
                    elif quality_type == 'HD' or quality_type == 'HDP':
                        quality = 2
                    elif quality_type == 'SD':
                        quality = 1
                    else:
                        quality = 0
                    logging.info('quality:{},bitrate:{}'.format(quality,bitrate))
                    if quality >= max_quality and bitrate >= max_bitrate:
                        bestfileindex = index
                        max_quality = quality
                        max_bitrate = bitrate
            logging.info('bestfileindex:{},quality:{},bitrate:{}'.format(bestfileindex,max_quality,max_bitrate))
            if bestfileindex == 100:
                logging.info('[ERROR], ERROR bestfileindex')
                continue
            for index in range(0,len(filenamelist)):
                if index != bestfileindex:
                    jpgfile = filenamelist[index]+'.jpg'
                    mp4file = filenamelist[index]+'.mp4'
                    logging.info('delete file:{},{}'.format(jpgfile,mp4file))
                    shutil.move(jpgfile,os.path.join('/home/dev/trash/',os.path.split(jpgfile)[1]))
                    shutil.move(mp4file,os.path.join('/home/dev/trash/',os.path.split(mp4file)[1]))
        logging.info('去重结束')
    def compact(self,folder):
        # ffmpeg -y -i in_a_0.wav -i in_a_1.wav -filter_complex "[0:a] silenceremove=stop_periods=1:stop_duration=1:stop_threshold=-50dB [first], [1:a] silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB [second],aevalsrc=exprs=0:d=1.5[silence],[first] [silence] [second] concat=n=3:v=0:a=1[outa]" -map [outa] out.wav
        path = Path(os.path.join(self.video_path,folder))
        fd = open(os.path.join(self.video_path,'filelist.txt'),'w+')
        filelist = []
        for i in path.glob("**/*.mp4"):
            # logging.info(i)
            filelist.append(i)
            fd.write('file \'{}\'\n'.format(i))
        fd.close()
        ffmpegstr = 'ffmpeg -f concat -safe 0 -i {} -c copy {}'.format(os.path.join(self.video_path,'filelist.txt'),os.path.join(self.video_path,'output.mkv'),)
        paramsstr = ''
        filterstr = ''
        filter2str = ''
        for index in range(0,len(filelist)):
            paramsstr = paramsstr+' -i \'{}\''.format(filelist[index])
            filterstr = filterstr+'[{}:v:0]scale=720:1270[v{}];'.format(index,index)
            filter2str = filter2str+'[v{}][{}:a:0]'.format(index,index)
        ffmpegstr = 'ffmpeg{} -filter_complex "{}{}concat=n={}:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx265 -crf 26 {}'.format(
            paramsstr,filterstr,filter2str,len(filelist),os.path.join(self.video_path,'output1.mp4')
        )
        # ffmpeg -i input1.mp4 -i input2.webm -i input3.mov \
        # -filter_complex "[0:v:0]scale=720:1270[v0];[1:v:0]scale=720:1270[v1];[2:v:0]scale=720:1270[v2];[v0][0:a:0][v1][1:a:0][v2][2:a:0]concat=n=3:v=1:a=1[outv][outa]" \
        # -map "[outv]" -map "[outa]" output.mkv
        print(ffmpegstr)
        os.system(ffmpegstr)
    def rename(self):
        for root, dirs, files in os.walk(self.img_path): # 遍历目录和子目录下的所有文件
            for file in files:
                old_name = os.path.join(root, file) # 拼接原始文件的完整路径
                new_name = self.filtern(file) # 使用正则表达式替换文件名中的空格为下划线
                if new_name != file:
                    logging.info('重命名：{} to {}'.format(file,new_name))
                    new_name = os.path.join(root, new_name) # 拼接新的文件的完整路径
                    os.rename(old_name, new_name) # 重命名文件
        for root, dirs, files in os.walk(self.video_path): # 遍历目录和子目录下的所有文件
            for file in files:
                old_name = os.path.join(root, file) # 拼接原始文件的完整路径
                new_name = self.filtern(file) # 使用正则表达式替换文件名中的空格为下划线
                if new_name != file:
                    logging.info('重命名：{} to {}'.format(file,new_name))
                    new_name = os.path.join(root, new_name) # 拼接新的文件的完整路径
                    os.rename(old_name, new_name) # 重命名文件
    # 随机获取视频并自动剪辑
    def randomvideo(self):
        # 获取目录中的所有视频文件
        video_exts = [".mp4", ".avi", ".mkv", ".flv"] # 视频文件的扩展名
        video_files = [] # 存放视频文件的列表
        filter_keyword = '关键字' #关键字
        video_dir = self.video_path + '/收藏' # 你要获取的目录路径
        for root, dirs, files in os.walk(video_dir): # 遍历目录及子目录
            for file in files: # 遍历文件
                if os.path.splitext(file)[1] in video_exts: # 判断文件是否是视频文件
                    if filter_keyword is not None and filter_keyword not in file:
                        continue
                    video_files.append(os.path.join(root, file)) # 将视频文件的完整路径添加到列表中

        # 随机选择视频文件，直到总时长达到5到6分钟
        total_duration = 0 # 单位为秒
        keywords = []
        keywordflag = False
        selected_files = []
        selected_files_time = []
        while total_duration < 180:
            # 使用random.sample随机抽取一个视频文件
            selected_file = random.sample(video_files, 1)[0]
            for keyword in keywords:
                if keyword in selected_file:
                    keywordflag = True
                    break
            if keywordflag == False and len(keywords) !=0:
                continue
            video_path = os.path.join(video_dir, selected_file)
            media_info = MediaInfo.parse(video_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    # pprint(track.to_data())
                    bit_rate=track.bit_rate
                    format=track.format
                    duration=track.duration
                    frame_rate=track.frame_rate
                    internet_media_type=track.internet_media_type
                    height=track.height
                    width=track.width
                    break
            if height < width:
                continue
            duration = duration / 1000
            if duration > 30:
                duration = 10
            total_duration += duration
            selected_files.append(selected_file)
            selected_files_time.append(int(duration))

        # # 创建一个文件列表
        # file_list = "filelist.txt"
        # if os.path.exists(file_list): # 判断文件是否存在
        #     os.remove(file_list) # 如果存在则删除
        # with open(file_list, "w") as f:
        #     for file in selected_files:
        #         file_path = os.path.join(video_dir, file)
        #         f.write(f"file '{file_path}'\n")

        inputtext = ''
        for item in range(0,len(selected_files)):
            inputtext = inputtext + '-i "{}" '.format(selected_files[item].replace('"',r'\"'))

        concatstr0 = ''
        # text0 = "drawtext=fontfile=simhei.ttf:text=\'Hello World\':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable=\'between(t,0,5)\'[vf];"
        for item in range(0,len(selected_files)):
            text1 = "drawtext=fontfile=./yahei.ttf:text=\'{}\':x=w-tw-10:y=h-lh-10:fontcolor=white:fontsize=28:borderw=2:bordercolor=black".format(re.sub(r"[^\u4e00-\u9fa5a-zA-Z]+", "", os.path.basename(selected_files[item])[:20]))
            text2 = "drawtext=fontfile=./yahei.ttf:text=\'%{{eif\:{}-t\:d}}\':x=w-1080+100:y=h-lh-10:fontcolor=white:fontsize=40:borderw=2:bordercolor=black".format(selected_files_time[item])
            concatstr0 = concatstr0 + '[{}:v]trim=duration={},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,{},{}[v{}];'.format(item,selected_files_time[item],text1,text2,item)

        concatstr1 = ''
        for item in range(0,len(selected_files)):
            concatstr1 = concatstr1 + '[v{}]'.format(item)
        concatstr = '-filter_complex "{}{}concat=n={}:v=1:a=0[v]"'.format(concatstr0,concatstr1,len(selected_files))
        now = datetime.now()
        ffmpegstr = 'ffmpeg -y {} {} -map "[v]" -c:v libx264 -preset ultrafast -crf 20 -r 30 "{}output-{}.mp4"'.format(inputtext,concatstr,'/mnt/disk2/test/',now.strftime("%Y-%m-%d-%H-%M-%S"))
        print(ffmpegstr)
        os.system(ffmpegstr)
                
class CheckXhsFavDown(CheckXhsDown):
    def __init__(self, conn):
        super().__init__(conn)
        self.checktype = 1
    def check(self):
        super().check()
        for root, dirs, files in os.walk("xhsdown/faved/20240323"):
            for file in files:
                file1 = os.path.join(root, file)
                with open(file1, 'r', encoding='utf-8') as json_file:
                    rjson = json.load(json_file)
                    # print(rjson)
                    datalist = rjson.get('data').get('notes')
                    if datalist is None:
                        logging.info('datalist is none')
                        continue
                    logging.info('datalist load ok,{}'.format(file))  
                    self.jsonLoad(datalist)

    def download(self):
        super().download()


class CheckXhsUserDown(CheckXhsDown):
    def __init__(self, conn):
        super().__init__(conn)
        self.checktype = 2

    def check(self):
        super().check()
        for root, dirs, files in os.walk("xhsdown/user/用户名"):
            for file in files:
                file1 = os.path.join(root, file)
                with open(file1, 'r', encoding='utf-8') as json_file:
                    rjson = json.load(json_file)
                    # print(rjson)
                    datalist = rjson.get('data').get('notes')
                    if datalist is None:
                        logging.info('datalist is none')
                        continue
                    self.jsonLoad(datalist)

    def download(self):
        super().download()
