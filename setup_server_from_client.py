#!/usr/bin/env python3
"""
从绝区零客户端提取配置并生成服务器 state。
所有数据均来自客户端，不依赖服务端已有配置。
自动检测客户端目录结构 (ZenlessZoneZeroBeta_Data / ZenlessZoneZero_Data)。
输出日志到文件。已存在的文件会在写入前自动备份。

用法:
  python3 setup_server_from_client.py \
    --client "/mnt/d/zzzz/CNBetaWin2.8.1" \
    --tentacle "/home/wsl/zzz/Tentacle" \
    --output-dir "./server_state"
"""

import argparse
import base64
import hashlib
import logging
import os
import re
import shutil
import struct
import sys
from datetime import datetime


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


def backup_if_exists(filepath, backup_dir):
    """如果文件已存在，复制到 backup_dir 备份"""
    if not os.path.exists(filepath):
        return
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rel = os.path.relpath(filepath, os.path.commonpath([filepath, backup_dir]))
    flat_name = rel.replace(os.sep, "__")
    dst = os.path.join(backup_dir, f"{ts}__{flat_name}")
    shutil.copy2(filepath, dst)
    logging.info("备份: %s -> %s", filepath, dst)


def md5_u64(data):
    return int.from_bytes(hashlib.md5(data).digest()[:8], "little", signed=False)


def der_len(n):
    if n < 0x80: return bytes([n])
    if n < 0x100: return b'\x81' + bytes([n])
    return b'\x82' + struct.pack(">H", n)


def der_int(data):
    if data[0] & 0x80: data = b'\x00' + data
    return b'\x02' + der_len(len(data)) + data


def detect_data_dir(client_dir):
    """自动检测客户端数据目录名"""
    for name in ["ZenlessZoneZeroBeta_Data", "ZenlessZoneZero_Data"]:
        path = os.path.join(client_dir, name, "StreamingAssets")
        if os.path.isdir(path):
            return name
    return None


def parse_version_branch(version):
    """从版本号推断 CDN branch 和路径前缀"""
    m = re.match(r"CN(Beta|PROD)(Win|Android|iOS)([\d.]+)", version)
    if m:
        env, platform, ver = m.group(1), m.group(2), m.group(3)
        branch = "beta_live" if env == "Beta" else "cn_live"
        return branch, platform, ver
    return "beta_live", "Win", "0.0.0"


def generate_server_keypair(bits=512):
    """生成服务端 RSA 密钥对 (PKCS#1 格式)"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=bits, backend=default_backend()
    )
    server_priv_der = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )

    pub = private_key.public_key().public_numbers()
    modulus = pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")
    exponent = pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")
    server_pub_der = b'\x30' + der_len(len(der_int(modulus) + der_int(exponent))) + der_int(modulus) + der_int(exponent)

    mod_b64 = base64.b64encode(modulus).decode()
    exp_b64 = base64.b64encode(exponent).decode()
    xml_key = "<RSAKeyValue><Exponent>{}</Exponent><Modulus>{}</Modulus></RSAKeyValue>".format(exp_b64, mod_b64)

    return server_priv_der, server_pub_der, xml_key


def generate_client_keypair(bits=1024):
    """生成客户端 RSA 密钥对，仅导出公钥 (PKCS#1 RSAPublicKey 格式)"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=bits, backend=default_backend()
    )

    pub = private_key.public_key().public_numbers()
    modulus = pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")
    exponent = pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")
    client_pub_der = b'\x30' + der_len(len(der_int(modulus) + der_int(exponent))) + der_int(modulus) + der_int(exponent)

    return client_pub_der


def extract_tentacle_rsa(tentacle_dir):
    """读取 Tentacle 中的原始 server_public_key.xml (仅供参考)"""
    xml_path = os.path.join(tentacle_dir, "assets", "server_public_key.xml")
    if not os.path.exists(xml_path):
        return None
    content = read_file(xml_path).decode("utf-8")
    return content.strip()


def extract_version_info(client_dir):
    """从客户端提取版本信息，自动检测目录结构"""
    data_dir = detect_data_dir(client_dir)
    if data_dir is None:
        logging.error("未找到 StreamingAssets 目录: %s", client_dir)
        logging.error("尝试过的目录: ZenlessZoneZeroBeta_Data, ZenlessZoneZero_Data")
        return None

    logging.info("检测到数据目录: %s", data_dir)

    streaming = os.path.join(client_dir, data_dir, "StreamingAssets")
    persistent = os.path.join(client_dir, data_dir, "Persistent")
    info = {}

    for key in ["data_revision", "res_revision", "audio_revision", "silence_revision"]:
        path = os.path.join(streaming, key)
        if os.path.exists(path):
            info[key] = read_file(path).decode().strip()
            logging.info("  %s = %s", key, info[key])
        else:
            logging.warning("  %s: 未找到", key)

    for key in ["data_version", "res_version", "audio_version", "silence_version"]:
        path = os.path.join(streaming, key)
        if os.path.exists(path):
            data = read_file(path)
            info[f"{key}_size"] = len(data)
            info[f"{key}_md5"] = md5_u64(data)
            logging.info("  %s: %d bytes, md5=%d", key, len(data), info[f"{key}_md5"])
        else:
            logging.warning("  %s: 未找到", key)

    base_rev_path = os.path.join(persistent, "base_revision")
    if os.path.exists(base_rev_path):
        data = read_file(base_rev_path).strip()
        info["base_revision_size"] = len(data)
        info["base_revision_md5"] = md5_u64(data)
        logging.info("  base_revision: %s (%d bytes, md5=%d)", data.decode(), len(data), info["base_revision_md5"])

    vi_path = os.path.join(client_dir, "version_info")
    if os.path.exists(vi_path):
        info["version"] = read_file(vi_path).decode().strip()
    else:
        info["version"] = "CNBetaWin3.0.1"
        logging.warning("  version_info: 未找到，使用默认 %s", info["version"])
    logging.info("  version = %s", info["version"])

    info["_data_dir"] = data_dir
    return info


def write_state_files(output_dir, server_priv_der, client_pub_der, ver_info, backup_dir):
    """生成所有 state 目录文件，写入前自动备份已存在的文件"""
    import secrets

    ver = ver_info.get("version", "CNBetaWin3.0.1")
    branch, platform, _ = parse_version_branch(ver)

    rsa_dir = os.path.join(output_dir, "rsa", "3")
    os.makedirs(rsa_dir, exist_ok=True)

    backup_if_exists(os.path.join(rsa_dir, "server_private_key.der"), backup_dir)
    with open(os.path.join(rsa_dir, "server_private_key.der"), "wb") as f:
        f.write(server_priv_der)
    logging.info("写入 rsa/3/server_private_key.der (%d bytes, PKCS#1)", len(server_priv_der))

    backup_if_exists(os.path.join(rsa_dir, "client_public_key.der"), backup_dir)
    with open(os.path.join(rsa_dir, "client_public_key.der"), "wb") as f:
        f.write(client_pub_der)
    logging.info("写入 rsa/3/client_public_key.der (%d bytes, PKCS#1 RSAPublicKey)", len(client_pub_der))

    # Gateway
    gw_dir = os.path.join(output_dir, "gateway")
    os.makedirs(gw_dir, exist_ok=True)
    gw_file = os.path.join(gw_dir, "server")
    backup_if_exists(gw_file, backup_dir)
    with open(gw_file, "w") as f:
        f.write("title = server\n")
        f.write("dispatch_url = http://127.0.0.1:10100/query_gateway/server\n")
        f.write("versions = {}\n".format(ver))
        f.write("ip = 127.0.0.1\n")
        f.write("port = 20501\n")
    logging.info("写入 gateway/server (version=%s)", ver)

    # Version
    ver_dir = os.path.join(output_dir, "version")
    os.makedirs(ver_dir, exist_ok=True)
    ver_file = os.path.join(ver_dir, ver)
    backup_if_exists(ver_file, backup_dir)
    dr = ver_info.get("data_revision", "0")
    rr = ver_info.get("res_revision", "0")
    ar = ver_info.get("audio_revision", "0")
    sr = ver_info.get("silence_revision", "0")
    dvs = ver_info.get("data_version_size", 0)
    dvm = ver_info.get("data_version_md5", 0)
    rvs = ver_info.get("res_version_size", 0)
    rvm = ver_info.get("res_version_md5", 0)
    avs = ver_info.get("audio_version_size", 0)
    avm = ver_info.get("audio_version_md5", 0)
    svs = ver_info.get("silence_version_size", 0)
    svm = ver_info.get("silence_version_md5", 0)
    brs = ver_info.get("base_revision_size", 0)
    brm = ver_info.get("base_revision_md5", 0)

    with open(ver_file, "w") as f:
        f.write("data_base_url = https://autopatchcn.juequling.com/design_data/{}/output_{}_CHANGEME/client/\n".format(branch, dr))
        f.write("data_revision = {}\n".format(dr))
        f.write('data_md5_files = [{{"fileName":"data_version","fileSize":{},"fileMD5":"{}"}}]\n'.format(dvs, dvm))
        f.write("res_base_url = https://autopatchcn.juequling.com/game_res/{}/output_{}_CHANGEME/client/\n".format(branch, rr))
        f.write("branch = {}\n".format(branch))
        f.write("audio_revision = {}\n".format(ar))
        f.write("res_revision = {}\n".format(rr))
        f.write('res_md5_files = [{{"fileName":"res_version","fileSize":{},"fileMD5":"{}"}},{{"fileName":"audio_version","fileSize":{},"fileMD5":"{}"}},{{"fileName":"base_revision","fileSize":{},"fileMD5":"{}"}}]\n'.format(rvs, rvm, avs, avm, brs, brm))
        f.write("silence_base_url = https://autopatchcn.juequling.com/design_data/{}/output_{}_CHANGEME/client_silence/\n".format(branch, sr))
        f.write("silence_revision = {}\n".format(sr))
        f.write('silence_md5_files = [{{"fileName":"silence_version","fileSize":{},"fileMD5":"{}"}}]\n'.format(svs, svm))
        f.write("cdn_check_url = https://autopatchcn.juequling.com/nap_test.txt\n")
    logging.info("写入 version/%s (branch=%s, data_rev=%s)", ver, branch, dr)

    # XOR pad
    xor_dir = os.path.join(output_dir, "xorpad")
    os.makedirs(xor_dir, exist_ok=True)
    seed = secrets.token_bytes(16)
    ec2b_xorpad = secrets.token_bytes(2048)
    ec2b_raw = b"Ec2b" + struct.pack("<I", 16) + seed + struct.pack("<I", 2048) + ec2b_xorpad
    backup_if_exists(os.path.join(xor_dir, "ec2b"), backup_dir)
    with open(os.path.join(xor_dir, "ec2b"), "w") as f:
        f.write(base64.b64encode(ec2b_raw).decode())
    logging.info("写入 xorpad/ec2b (%d bytes, Ec2b+seed(16)+xorpad(2048))", len(ec2b_raw))

    xorpad = secrets.token_bytes(4096)
    backup_if_exists(os.path.join(xor_dir, "bytes"), backup_dir)
    with open(os.path.join(xor_dir, "bytes"), "wb") as f:
        f.write(xorpad)
    logging.info("写入 xorpad/bytes (4096 bytes)")

    # Account
    acc_dir = os.path.join(output_dir, "account")
    os.makedirs(acc_dir, exist_ok=True)
    backup_if_exists(os.path.join(acc_dir, "1"), backup_dir)
    with open(os.path.join(acc_dir, "1"), "w", newline="") as f:
        f.write(".{ .player_uid = 1 }")
    logging.info("写入 account/1")

    # Player dirs
    for sub in ["avatar", "buddy", "equip", "weapon", "hall/1", "hadal_zone"]:
        os.makedirs(os.path.join(output_dir, "player", "1", sub), exist_ok=True)

    return ver


def generate_bash_script(new_xml, tentacle_xml, ver, output_path):
    """生成 bash 辅助脚本"""
    script = """#!/bin/bash
# ============================================================
# 服务器辅助脚本 (已由 setup_server_from_client.py 生成)
# ============================================================

STATE_DIR="${{1:-$HOME/server/state}}"
VERSION="{ver}"

echo "=== 服务器启动 ==="
echo "State:    $STATE_DIR"
echo "Version:  $VERSION"
echo ""

missing=0
for f in \\
    "$STATE_DIR/gateway/server" \\
    "$STATE_DIR/version/$VERSION" \\
    "$STATE_DIR/rsa/3/server_private_key.der" \\
    "$STATE_DIR/rsa/3/client_public_key.der" \\
    "$STATE_DIR/xorpad/ec2b" \\
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
echo "  {new_xml}"
echo ""
echo "Tentacle 原始 XML:"
echo "  {tentacle_xml}"
""".format(
        ver=ver,
        new_xml=new_xml or "(未生成)",
        tentacle_xml=tentacle_xml or "(未找到)",
    )

    with open(output_path, "w", newline="\n") as f:
        f.write(script)
    os.chmod(output_path, 0o755)
    logging.info("辅助脚本: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="从绝区零客户端提取配置并生成服务器 state")
    parser.add_argument("--client", required=True, help="客户端根目录 (包含 StreamingAssets 的上层)")
    parser.add_argument("--tentacle", default="/home/wsl/zzz/Tentacle", help="Tentacle 源码目录 (仅读取原始 XML 参考)")
    parser.add_argument("--output-dir", default="./server_state", help="输出 state 目录")
    parser.add_argument("--bash-script", default="./start_server.sh", help="辅助 bash 脚本路径")
    parser.add_argument("--log", default=None, help="日志文件路径 (默认: <output-dir>/setup.log)")
    args = parser.parse_args()

    # 日志
    log_path = args.log or os.path.join(args.output_dir, "setup.log")
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info("=== 从客户端提取配置 ===")
    logging.info("客户端: %s", args.client)
    logging.info("Tentacle: %s (仅读取)", args.tentacle)
    logging.info("输出目录: %s", args.output_dir)
    logging.info("日志文件: %s", log_path)

    backup_dir = os.path.join(args.output_dir, "backup")

    # RSA
    logging.info("[RSA 密钥生成]")
    try:
        server_priv_der, server_pub_der, server_xml = generate_server_keypair(bits=512)
        logging.info("服务端: 512-bit RSA 密钥对 (PKCS#1, %d bytes)", len(server_priv_der))
        client_pub_der = generate_client_keypair(bits=1024)
        logging.info("客户端: 1024-bit RSA 公钥 (PKCS#1 RSAPublicKey, %d bytes)", len(client_pub_der))
    except ImportError:
        logging.error("需要 python3-cryptography: pip3 install cryptography")
        return

    # Tentacle RSA (仅读取参考)
    logging.info("[Tentacle RSA (参考)]")
    tentacle_xml = extract_tentacle_rsa(args.tentacle)
    if tentacle_xml:
        logging.info("找到 server_public_key.xml")
    else:
        logging.warning("未找到 server_public_key.xml")

    # 版本信息
    logging.info("[版本信息]")
    ver_info = extract_version_info(args.client)
    if ver_info is None:
        logging.error("无法提取版本信息，退出")
        return

    # 写入文件 (自动备份已存在的旧文件)
    logging.info("[写入 state 文件]")
    ver = write_state_files(args.output_dir, server_priv_der, client_pub_der, ver_info, backup_dir)

    # 辅助脚本
    logging.info("[生成辅助脚本]")
    generate_bash_script(server_xml, tentacle_xml, ver, args.bash_script)

    logging.info("=== 完成 ===")
    logging.info("State 目录: %s", os.path.abspath(args.output_dir))
    logging.info("备份目录: %s", os.path.abspath(backup_dir))
    logging.info("日志文件: %s", os.path.abspath(log_path))
    logging.info("CDN URL 中的 CHANGEME 需替换为实际 output hash")


if __name__ == "__main__":
    main()
