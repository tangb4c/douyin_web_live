#!/usr/bin/env bash
#########################################################################
# Author: blaketang
# Created Time: Mon 27 Mar 2023 09:57:16 AM CST
# File Name: encoding_finished_video.sh
# Description:
#########################################################################

# 怎么正经的实现shell脚本单例运行？ - 腾讯云开发者社区-腾讯云
# https://cloud.tencent.com/developer/article/1634267
# 单实例运行
[ "${FLOCKER}" != "$0" ] && exec env FLOCKER="$0" flock -en  "$0"  "$0"  "$@"

echo "开始运行"

live_dir=$HOME/output/douyin_web_live/live
dst_dir=$HOME/output/douyin_web_live/encoded
recycle_dir=$HOME/output/douyin_web_live/recycle

cd "$live_dir" || (echo "$live_dir 不存在" && exit 1)
find . -type f -name "*.mp4" -printf '%P\n' | while IFS= read -r video_file; do
  # 当lsof无任何输出时，会返回非零错误码
  if lsof "$video_file" 2>/dev/null; then
    echo "视频文件正在被占用. $video_file"
    continue
  fi
  echo "准备处理视频:$video_file"

  video_path=$(dirname "$video_file")
  output_dir="$dst_dir/$video_path"
  echo "目标目录:$output_dir 目标文件: $output_file"
  mkdir -p "$output_dir"

  if [[ $video_file =~ .h264.mp4$ ]]; then
    mv -fv "$video_file" "$output_dir"
  else
    title=$(basename "$video_file")
    output_file="$dst_dir/${title%%.*}.h264.mp4"
    echo -e "视频:$video_file\n\t转换为:$output_file"
    taskset -c 1-14 /usr/local/bin/ffmpeg \
      -hide_banner \
      -y \
      -fflags +genpts \
      -i "$video_file" \
      -metadata title="$title" \
      -c:v libx264 -crf 28 -preset slow \
      -ac 1 -c:a libfdk_aac -profile:a aac_he -b:a 28k \
      "$output_file"
    if [ $? -eq 0 ]; then
      echo "ffmpeg 编码成功，删除原始文件"
      output_recycle_dir="$recycle_dir/$video_path"
      mkdir -p "$output_recycle_dir"
      mv -fv "$video_file" "$output_recycle_dir"
    else
      echo "ffmpeg 编码失败.encoding failed"
    fi
  fi
done
