#!/usr/bin/env bash
#########################################################################
# Author: blaketang
# Created Time: Mon 27 Mar 2023 09:57:16 AM CST
# File Name: encoding_finished_video.sh
# Description:
#########################################################################
msg() {
  echo -e "\e[32m$(date '+%F %T') $*\e[0m"
}
err() {
  echo -e "\e[31m$(date '+%F %T') $*\e[0m"
}

if pgrep ffmpeg >/dev/null; then
  # msg '已有ffmpeg正在运行，本次运行中止'
  exit 1
fi
# 5秒后再次检查（避免两个ffmpeg执行间隔，出现并行冲突）
sleep 10
if pgrep ffmpeg >/dev/null; then
  msg '再次检测：已有ffmpeg正在运行，本次运行中止'
  exit 1
fi

# 怎么正经的实现shell脚本单例运行？ - 腾讯云开发者社区-腾讯云
# https://cloud.tencent.com/developer/article/1634267
# 单实例运行
[ "${FLOCKER}" != "$0" ] && exec env FLOCKER="$0" flock -en "$0" "$0" "$@"

msg "开始运行"

live_dir=$HOME/output/douyin_web_live/live
dst_dir=$HOME/output/douyin_web_live/encoded
recycle_dir=$HOME/output/douyin_web_live/recycle
badfile_dir=$HOME/output/douyin_web_live/badfile

mkdir -p "$dst_dir" "$recycle_dir" "$badfile_dir"

cd "$live_dir" || (echo "$live_dir 不存在" && exit 1)
find . -type f \( -name "*.flv" -o -name "*.mp4" -o -name "*.ts" \) -printf '%P\n' | while IFS= read -r video_file; do

  # 确保文件未被占用。当lsof无任何输出时，会返回非零错误码
  used_count=$(lsof "$video_file" 2>/dev/null | wc -l)
  if [ $used_count -ne 0 ]; then
    msg "视频文件正在被占用. $video_file"
    msg "$(lsof '$video_file')"
    continue
  fi

#  if [[ ! ( "$video_file" =~ "小夕颜" ) ]];then
#    msg "调试模式中，跳过$video_file"
#    continue
#  fi

  # 视频处理部分
  msg "准备处理视频:$video_file"
  video_path=$(dirname "$video_file")
  output_dir="$dst_dir/$video_path"
  car600p_dir="$output_dir/1024x600"
  audio_output_dir="$output_dir/audio"
  mkdir -p "$output_dir" "$audio_output_dir" "$car600p_dir"

  msg "目标目录:$output_dir 音频目录:$audio_output_dir"

  if [[ $video_file =~ .h264.mp4$ ]]; then
    mv -fv "$video_file" "$output_dir"
  else
    title=$(basename "$video_file")
    # 编码成h264视频
    output_file="$output_dir/${title%%.*}.h264.NR.mp4"
    # 生成适合车机1024x600分辨率的视频
    output_600p_file="$car600p_dir/${title%%.*}.h264.NR.600p.mp4"
    # 音频处理部分
    audio_output_file="$audio_output_dir/${title%%.*}.aac.m4a"

    msg "视频:$video_file\t转换为:$output_file\n\t"

    taskset -c 1-15 /usr/local/bin/ffmpeg \
      -nostdin \
      -nostats \
      -hide_banner \
      -y \
      -i "$video_file" \
      -metadata title="$title" \
      -filter_complex \
      "[0:v]split[v1][v2];[v2]crop=h=iw:y=ih*650/1920,scale=-1:600[carv];[0:a]asplit[a1][a2];[a2]highpass=f=200,lowpass=f=3000,volume=3dB[cara]" \
      -map "[v1]" -map "[carv]" -c:v libx264 -crf 28 -preset veryslow \
      -map "[cara]" -ac 1 -ar 32000 -c:a libfdk_aac -profile:a aac_he -b:a 24k \
      -f tee \
      "[select=\'v:0,a\':f=mp4]$output_file|
       [select=\'v:1,a\':f=mp4]$output_600p_file" \
      -map "[a1]" -c:a libfdk_aac -profile:a aac_he -b:a 64k \
      "$audio_output_file"

    ret_code=$?
    if [ $ret_code -eq 0 ]; then
      msg "ffmpeg 编码成功，移动原始文件"
      output_recycle_dir="$recycle_dir/$video_path"
      mkdir -p "$output_recycle_dir" && mv -fv "$video_file" "$output_recycle_dir"
      # 处理成功1个文件即退出
      break
    else
      err "ffmpeg 音频编码失败. ret:$ret_code"
      output_badfile_dir="$badfile_dir/$video_path"
      mkdir -p "$output_badfile_dir" && mv -fv "$video_file" "$output_badfile_dir"
    fi
  fi
done

#   #       -ac 1 -c:a libfdk_aac -profile:a aac_he_v2 -b:a 28k \
#    # 适合分享、对话场景      -af "highpass=f=200, lowpass=f=3000" -ac 1 -ar 32000 -c:a libfdk_aac -b:a 24k
#    taskset -c 1-15 /usr/local/bin/ffmpeg \
#      -nostdin \
#      -nostats \
#      -hide_banner \
#      -y \
#      -fflags +genpts \
#      -i "$video_file" \
#      -metadata title="$title" \
#      -c:v libx264 -crf 28 -preset veryslow \
#      -af "highpass=f=200, lowpass=f=3000, volume=3dB" -ac 1 -ar 32000 -c:a libfdk_aac -profile:a aac_he -b:a 24k \
#      "$output_file"
#
#    ret_code=$?
#    if [ $ret_code -ne 0 ]; then
#      err "ffmpeg视频编码失败. ret:$ret_code"
#      mkdir -p "$badfile_dir"
#      mv -fv "$video_file" "$badfile_dir"
#      continue
#    fi
#
#    # 生成适合车机1024x600分辨率的视频
#    output_600p_file="$car600p_dir/${title%%.*}.h264.NR.600p.mp4"
#    taskset -c 1-15 /usr/local/bin/ffmpeg \
#      -nostdin \ -nostats \
#      -hide_banner \
#      -y \
#      -fflags +genpts \
#      -i "$video_file" \
#      -metadata title="$title" \
#      -filter:v 'crop=h=iw:y=ih*650/1920,scale=-1:600' \
#      -c:v libx264 -crf 28 -preset veryslow \
#      -af "highpass=f=200, lowpass=f=3000, volume=3dB" -ac 1 -ar 32000 -c:a libfdk_aac -profile:a aac_he -b:a 24k \
#      "$output_600p_file"
#
#    ret_code=$?
#    if [ $ret_code -ne 0 ]; then
#      err "ffmpeg视频编码车机1024x600失败. ret:$ret_code"
#      mkdir -p "$badfile_dir"
#      mv -fv "$video_file" "$badfile_dir"
#      continue
#    fi
#
#    # 音频处理部分
#    audio_output_file="$audio_output_dir/${title%%.*}.aac.m4a"
#    msg "从视频:$video_file\t提取音频:$audio_output_file"
#    /usr/local/bin/ffmpeg \
#      -nostdin \
#      -nostats \
#      -hide_banner \
#      -y \
#      -i "$video_file" \
#      -metadata title="$title" \
#      -vn \
#      -c:a libfdk_aac -profile:a aac_he -b:a 64k \
#      "$audio_output_file"
#
#    ret_code=$?
#    if [ $ret_code -eq 0 ]; then
#      msg "ffmpeg 编码成功，移动原始文件"
#      output_recycle_dir="$recycle_dir/$video_path"
#      mkdir -p "$output_recycle_dir"
#      mv -fv "$video_file" "$output_recycle_dir"
#      # 处理成功1个文件即退出
#      break
#    else
#      err "ffmpeg 音频编码失败. ret:$ret_code"
#      mkdir -p "$badfile_dir"
#      mv -fv "$video_file" "$badfile_dir"
#      continue
#    fi