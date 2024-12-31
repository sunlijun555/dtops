ps -fe|grep python3 |awk '{print $2}'|xargs -I {} kill -9 {} > /dev/null 2>&1
