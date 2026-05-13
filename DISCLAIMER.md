# Disclaimer / 声明

**This project is provided for educational and research purposes only.**
**本项目仅供学习与研究用途。**

---

## Explanation / 解释

### What this tool does / 本工具的功能

This tool reads configuration data from locally installed client files (such as version info, revision numbers, and data checksums) and uses them to generate a server-side `state` directory structure for local development and testing.

本工具从本地已安装的客户端文件中读取配置数据（如版本信息、修订号、数据校验值等），并利用这些信息生成服务端 `state` 目录结构，用于本地开发和调试。

### Data flow / 数据流向

```
Client (local, user-owned)
        |
        | Read only
        v
  setup_server_from_client.py
        |
        | Generate
        v
  server_state/ directory
```

All data originates from the user's own local installation. No external servers are contacted.

所有数据均来源于用户自己的本地安装。不连接任何外部服务器。
