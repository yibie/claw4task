#!/bin/bash
# Moltbook 发帖提醒脚本
# 用法: ./moltbook_reminder.sh <目标时间>
# 例如: ./moltbook_reminder.sh "17:38:00"

TARGET_TIME=$1

if [ -z "$TARGET_TIME" ]; then
    echo "用法: $0 <目标时间 HH:MM:SS>"
    echo "例如: $0 17:38:00"
    exit 1
fi

echo "🦞 Moltbook 发帖提醒器"
echo "======================"
echo "目标发布时间: $TARGET_TIME"
echo ""

while true; do
    CURRENT=$(date +%s)
    TARGET=$(date -j -f "%H:%M:%S" "$TARGET_TIME" +%s 2>/dev/null || date -d "$TARGET_TIME" +%s)
    
    if [ -z "$TARGET" ]; then
        echo "❌ 时间格式错误，使用 HH:MM:SS 格式"
        exit 1
    fi
    
    REMAINING=$((TARGET - CURRENT))
    
    if [ $REMAINING -le 0 ]; then
        echo ""
        echo "🎉 时间到了！可以发帖了！"
        echo "执行命令:"
        echo 'curl -sX POST https://www.moltbook.com/api/v1/posts \\'
        echo '  -H "Authorization: Bearer moltbook_sk_ebf3QzhgM4WmhrP82NJCxX6mt_Bfos9n" \\'
        echo '  -H "Content-Type: application/json" \\'
        echo '  -d @/tmp/post_collaboration.json'
        exit 0
    fi
    
    # 计算分钟和秒
    MINS=$((REMAINING / 60))
    SECS=$((REMAINING % 60))
    
    printf "\r⏳ 剩余时间: %02d:%02d  " $MINS $SECS
    sleep 1
done
