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

if pgrep ffmpeg >/dev/null;then
  msg '已有ffmpeg正在运行，本次运行中止'
  exit 1
fi
# 8分钟后再次检查
sleep 480
if pgrep ffmpeg >/dev/null;then
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

cd "$live_dir" || (echo "$live_dir 不存在" && exit 1)
find . -type f -name "*.mp4" -printf '%P\n' | while IFS= read -r video_file; do
  # 当lsof无任何输出时，会返回非零错误码
  used_count=$(lsof "$video_file" 2>/dev/null | wc -l)
  if [ $used_count -ne 0 ]; then
    msg "视频文件正在被占用. $video_file"
    msg "$(lsof '$video_file')"
    continue
  fi
  msg "准备处理视频:$video_file"

  video_path=$(dirname "$video_file")
  output_dir="$dst_dir/$video_path"
  msg "目标目录:$output_dir"
  mkdir -p "$output_dir"

  if [[ $video_file =~ .h264.mp4$ ]]; then
    mv -fv "$video_file" "$output_dir"
  else
    title=$(basename "$video_file")
    output_file="$output_dir/${title%%.*}.h264.NR.mp4"
    msg "视频:$video_file\t转换为:$output_file"
    #       -ac 1 -c:a libfdk_aac -profile:a aac_he_v2 -b:a 28k \
    # 适合分享、对话场景      -af "highpass=f=200, lowpass=f=3000" -ac 1 -ar 32000 -c:a libfdk_aac -b:a 24k
    taskset -c 1-15 /usr/local/bin/ffmpeg \
      -nostats \
      -hide_banner \
      -y \
      -fflags +genpts \
      -i "$video_file" \
      -metadata title="$title" \
      -c:v libx264 -crf 28 -preset veryslow \
      -af "highpass=f=200, lowpass=f=3000" -ac 1 -ar 32000 -c:a libfdk_aac -b:a 24k \
      "$output_file"
    if [ $? -eq 0 ]; then
      msg "ffmpeg 编码成功，移动原始文件"
      output_recycle_dir="$recycle_dir/$video_path"
      mkdir -p "$output_recycle_dir"
      mv -fv "$video_file" "$output_recycle_dir"
      # 处理成功1个文件即退出
      break
    else
      err "ffmpeg 编码失败.encoding failed"
    fi
  fi
done
