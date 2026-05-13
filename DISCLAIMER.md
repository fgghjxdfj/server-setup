# Disclaimer / 声明

**This project is provided for educational and research purposes only.**
**本项目仅供学习与研究用途。**

---

## Explanation / 解释

### What this tool does / 本工具的功能

This tool reads configuration data from locally installed client files (such as version info, revision numbers, and data checksums) and uses them to generate a server-side `state` directory structure for local development and testing.

本工具从本地已安装的客户端文件中读取配置数据（如版本信息、修订号、数据校验值等），并利用这些信息生成服务端 `state` 目录结构，用于本地开发和调试。

### What this tool does NOT do / 本工具不具备的功能

- It does **not** decrypt, crack, or reverse-engineer any binaries.
- It does **not** connect to any external servers.
- It does **not** distribute or include any copyrighted content.
- It does **not** bypass any authentication, DRM, or anti-cheat systems.
- It does **not** modify any client installation.

- 本工具**不**解密、破解或逆向工程任何可执行文件。
- 本工具**不**连接任何外部服务器。
- 本工具**不**发布或包含任何受版权保护的内容。
- 本工具**不**绕过任何认证、DRM 或反作弊系统。
- 本工具**不**修改任何客户端安装文件。

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
