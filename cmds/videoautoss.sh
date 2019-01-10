#!/usr/bin/env bash
# -*- coding: utf-8 -*-

cwd=`dirname "$0"`
expr "$0" : "/.*" > /dev/null || cwd=`(cd "$cwd" && pwd)`

[[ -n $DEBUG ]] && set -x -e

FRAME_FATE=1    # unit: frame#/sec
TIME_OFFSET=0   # unit: second

help() {
  echo "Usage: videoautoss <name> -c <camera#>"
  cat <<"EOF"

Options:
  <name>                    [Required] Video name
  -c, --camerano <num>      [Required] Camera number (1,2,3,..)
  -i, --input <videofile>   [Required] Input Video file (.mp4, wmv, ..)
  -d, --tmpdir <workingDir> [Optional] Working directory ("out" by default)
  -h, --help                Show this message

Example:
  videoautoss sportsgame1 -c 1 -i /path-to/sample_c1.mp4
  videoautoss sportsgame1 -c 1 -i /path-to/sample_c1.mp4 -d ~/work
EOF
}

process_video(){
  local videoname="$1"
  local camerano="$2"
  local inputvideo="$3"
  local tmpdir="$4"

  LOCAL_PATH=${tmpdir}/${videoname}/${camerano}
  if [ ! -d ${LOCAL_PATH} ]; then
    mkdir -p ${LOCAL_PATH}
  fi

  ffmpeg -i ${inputvideo} -ss $TIME_OFFSET -r ${FRAME_FATE} ${LOCAL_PATH}/${videoname}_${camerano}_%04d.jpg

  python processVideo.py -n ${videoname} -c ${camerano} -d ${LOCAL_PATH}
}

cmd_main(){
  videoname=""
  camerano=0
  inputvideo=""
  tmpdir="out"
  for arg in "$@"; do
    option=""
    if [ "${arg:0:1}" = "-" ]; then
      if [ "${arg:1:1}" = "-" ]; then
        option="${arg:2}"
        prevopt="${arg:2}"
      else
        index=1
        while o="${arg:$index:1}"; do
          [ -n "$o" ] || break
          option="$o"
          prevopt="$o"
          let index+=1
        done
      fi
      case "${option}" in
      "h" | "help" )
        help
        exit 0
        ;;
      esac
    else
      if [ "${prevopt}" = "" ]; then
        videoname="${arg}"
      else
        case "${prevopt}" in
        "c" | "camerano" )
          camerano="${arg}"
          ;;
        "i" | "input" )
          inputvideo="${arg}"
          ;;
        "d" | "tmpdir" )
          tmpdir="${arg}"
          ;;
        * )
          help >&2
          exit 1
          ;;
        esac
      fi
    fi
  done

  if [ ! ${inputvideo} ] || [ ! ${camerano} ] || [ ! ${videoname} ]; then
    help >&2
    exit 1
  fi
  if [[ "$(type ffmpeg &>/dev/null; echo $?)" -eq 1 ]]; then
    echo "Error: missing ffmpeg command" >&2
    echo "Please install ffmpeg (https://ffmpeg.org)" >&2
    exit 1
  fi
  if [[ "$(type processVideo.py &>/dev/null; echo $?)" -eq 1 ]]; then
    echo "Error: missing processVideo.py command" >&2
    exit 1
  fi
  if [ ! -d ${tmpdir} ]; then
    mkdir -p ${tmpdir}
  fi
  process_video ${videoname} ${camerano} ${inputvideo} ${tmpdir}
}

cmd_main "$@"
