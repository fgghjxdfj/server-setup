#!/bin/bash
# ============================================================
# 服务器辅助脚本 (已由 setup_server_from_client.py 生成)
# ============================================================

STATE_DIR="${1:-$HOME/server/state}"
VERSION="CNBetaWin3.0.1"

echo "=== 服务器启动 ==="
echo "State:    $STATE_DIR"
echo "Version:  $VERSION"
echo ""

missing=0
for f in \
    "$STATE_DIR/gateway/server" \
    "$STATE_DIR/version/$VERSION" \
    "$STATE_DIR/rsa/3/server_private_key.der" \
    "$STATE_DIR/rsa/3/client_public_key.der" \
    "$STATE_DIR/xorpad/ec2b" \
    "$STATE_DIR/xorpad/bytes"; do
    if [ ! -f "$f" ]; then
        echo "[MISS] $f"
        missing=$((missing + 1))
    fi
done

if [ $missing -gt 0 ]; then
    echo ""
    echo "有 $missing 个文件缺失，请先运行 setup_server_from_client.py"
    exit 1
fi

echo "所有配置文件就绪"
echo ""
echo "启动命令:"
echo "  cd ~/server"
echo "  export PATH=$HOME/zig:$PATH"
echo "  zig build run-dpsv -- -s $STATE_DIR &"
echo "  zig build run-gamesv -- -g server -s $STATE_DIR"
echo ""
echo "生成的服务端公钥 XML:"
echo "  <RSAKeyValue><Exponent>AQAB</Exponent><Modulus>zGmOGUxkhDQ5Bk5y4VTYC2leDaOF5bcnxU+tTMj6zYocDLHbDTwrV6qaHOLcZRX/35tgkbbCHe1qZZO+5jwGGQ==</Modulus></RSAKeyValue>"
echo ""
echo "Tentacle 原始 XML:"
echo "  <RSAKeyValue>
<Modulus>
d8zyiJhwWK1Gocou1iynAKbH9f27uAtqFWec+Rbr6G9JFzyAsqH2G7iKqPV60lItLgJ/jvcVyzPeE9eQ1h6Fjw==
</Modulus>
<Exponent>
AQAB
</Exponent>
</RSAKeyValue>"
