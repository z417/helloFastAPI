# LoadRunner 国密/签名加密 DLL

本目录提供 `gm_crypto.c`，用于编译给 LoadRunner C 脚本调用的加密 DLL。当前实现基于 OpenSSL EVP。

## 1. 导出接口

所有接口都返回错误码，并要求调用方传入输出缓冲区容量：

```c
extern int gm_random_hex(char *out_hex, int out_cap, int byte_len);
extern int gm_sha256_hex(const char *input, char *out_hex, int out_cap);
extern int gm_sm3_hex(const char *input, char *out_hex, int out_cap);

extern int gm_sm4_cbc_encrypt_hex(
    const char *plain,
    const char *key,
    char *out_iv_hex,
    int iv_cap,
    char *out_cipher_hex,
    int cipher_cap
);

extern int gm_sm4_cbc_encrypt_hex_key_hex(
    const char *plain,
    const char *key_hex,
    char *out_iv_hex,
    int iv_cap,
    char *out_cipher_hex,
    int cipher_cap
);

extern int gm_sm4_cbc_encrypt_hex_with_iv(
    const char *plain,
    const char *iv_hex,
    const char *key,
    char *out_cipher_hex,
    int cipher_cap
);

extern int gm_sm4_cbc_encrypt_hex_with_iv_key_hex(
    const char *plain,
    const char *iv_hex,
    const char *key_hex,
    char *out_cipher_hex,
    int cipher_cap
);

extern int gm_sm4_ecb_encrypt_block(
    const unsigned char *input_block,
    const char *key,
    unsigned char *output_block
);
```

返回码：

```c
#define GM_OK 0
#define GM_ERR_PARAM -1
#define GM_ERR_BUFFER_TOO_SMALL -2
#define GM_ERR_CRYPTO -3
#define GM_ERR_UNSUPPORTED -4
```

SM4 是 128 bit 分组密码，标准密钥长度固定为 16 字节。这里不做截断、不做补零，避免配置错误被静默掩盖。

支持两种 key 传入方式：

- `key`：16 字节字符串，例如 `hello_cinema_sm4`。
- `key_hex`：32 个 hex 字符，例如 `68656c6c6f5f63696e656d615f736d34`。

如果业务侧给的是口令或任意长度 secret，不应直接截断成 16 字节；推荐先在服务端和压测脚本统一约定 KDF，例如 `SM3(secret)` 后取前 16 字节，或使用标准 KDF/HKDF 派生出 16 字节 SM4 key。

如果 key 中可能包含 `\0`、非 ASCII 字节，或配置系统不方便表达原始字节，应使用 `key_hex` 接口。

## 2. API 使用说明

### `gm_random_hex`

生成安全随机数，并输出为小写 hex 字符串。

```c
int gm_random_hex(char *out_hex, int out_cap, int byte_len);
```

- `out_hex`：输出缓冲区。
- `out_cap`：输出缓冲区容量，至少为 `byte_len * 2 + 1`。
- `byte_len`：随机字节数，例如 `16` 会输出 32 个 hex 字符。
- 成功返回 `GM_OK`。

示例：

```c
char nonce[33];
int rc = gm_random_hex(nonce, sizeof(nonce), 16);
```

### `gm_sha256_hex`

计算输入字符串的 SHA-256，并输出 64 位小写 hex 摘要。

```c
int gm_sha256_hex(const char *input, char *out_hex, int out_cap);
```

- `input`：以 `\0` 结尾的字符串。
- `out_hex`：输出缓冲区。
- `out_cap`：至少为 `65`。

示例：

```c
char digest[65];
int rc = gm_sha256_hex("abc", digest, sizeof(digest));
```

### `gm_sm3_hex`

计算输入字符串的 SM3，并输出 64 位小写 hex 摘要。

```c
int gm_sm3_hex(const char *input, char *out_hex, int out_cap);
```

- `input`：以 `\0` 结尾的字符串。
- `out_hex`：输出缓冲区。
- `out_cap`：至少为 `65`。
- 常用于 `X-Signature` 签名。

示例：

```c
char signature[65];
int rc = gm_sm3_hex(payload, signature, sizeof(signature));
```

### `gm_sm4_cbc_encrypt_hex`

使用 16 字节字符串 key 自动生成随机 IV，执行 SM4-CBC-PKCS7 加密，并输出 `iv_hex` 和 `cipher_hex`。

```c
int gm_sm4_cbc_encrypt_hex(
    const char *plain,
    const char *key,
    char *out_iv_hex,
    int iv_cap,
    char *out_cipher_hex,
    int cipher_cap
);
```

- `plain`：明文字符串。
- `key`：正好 16 字节的字符串 key。
- `out_iv_hex`：输出 IV hex，容量至少 `33`。
- `iv_cap`：IV 输出缓冲区容量。
- `out_cipher_hex`：输出密文 hex。
- `cipher_cap`：密文输出缓冲区容量；最小建议按 `(strlen(plain) + 16) * 2 + 1` 预留。

示例：

```c
char iv_hex[33];
char cipher_hex[1024];
int rc = gm_sm4_cbc_encrypt_hex(
    "1700000000000:123456",
    "hello_cinema_sm4",
    iv_hex,
    sizeof(iv_hex),
    cipher_hex,
    sizeof(cipher_hex)
);
```

### `gm_sm4_cbc_encrypt_hex_key_hex`

功能同 `gm_sm4_cbc_encrypt_hex`，但 key 使用 32 字符 hex 表达，适合二进制 key、非 ASCII key 或配置中心只适合放文本的场景。

```c
int gm_sm4_cbc_encrypt_hex_key_hex(
    const char *plain,
    const char *key_hex,
    char *out_iv_hex,
    int iv_cap,
    char *out_cipher_hex,
    int cipher_cap
);
```

- `key_hex`：正好 32 个 hex 字符，表示 16 字节 SM4 key。

示例：

```c
char iv_hex[33];
char cipher_hex[1024];
int rc = gm_sm4_cbc_encrypt_hex_key_hex(
    "1700000000000:123456",
    "68656c6c6f5f63696e656d615f736d34",
    iv_hex,
    sizeof(iv_hex),
    cipher_hex,
    sizeof(cipher_hex)
);
```

### `gm_sm4_cbc_encrypt_hex_with_iv`

使用调用方传入的 IV 执行 SM4-CBC-PKCS7 加密。适合服务端要求指定 IV、复现问题或与固定测试向量对比。

```c
int gm_sm4_cbc_encrypt_hex_with_iv(
    const char *plain,
    const char *iv_hex,
    const char *key,
    char *out_cipher_hex,
    int cipher_cap
);
```

- `iv_hex`：正好 32 个 hex 字符，表示 16 字节 IV。
- `key`：正好 16 字节字符串 key。
- 生产请求通常优先用自动生成 IV 的 `gm_sm4_cbc_encrypt_hex`。

示例：

```c
char cipher_hex[1024];
int rc = gm_sm4_cbc_encrypt_hex_with_iv(
    "1700000000000:123456",
    "83c2ccbb351c56c9fbf0bb74afbad2b2",
    "hello_cinema_sm4",
    cipher_hex,
    sizeof(cipher_hex)
);
```

### `gm_sm4_cbc_encrypt_hex_with_iv_key_hex`

功能同 `gm_sm4_cbc_encrypt_hex_with_iv`，但 key 使用 32 字符 hex 表达。

```c
int gm_sm4_cbc_encrypt_hex_with_iv_key_hex(
    const char *plain,
    const char *iv_hex,
    const char *key_hex,
    char *out_cipher_hex,
    int cipher_cap
);
```

示例：

```c
char cipher_hex[1024];
int rc = gm_sm4_cbc_encrypt_hex_with_iv_key_hex(
    "1700000000000:123456",
    "83c2ccbb351c56c9fbf0bb74afbad2b2",
    "68656c6c6f5f63696e656d615f736d34",
    cipher_hex,
    sizeof(cipher_hex)
);
```

### `gm_sm4_ecb_encrypt_block`

加密单个 16 字节 SM4-ECB 分组，不做填充，不输出 hex。主要用于算法对照测试，不推荐业务请求使用 ECB 模式。

```c
int gm_sm4_ecb_encrypt_block(
    const unsigned char *input_block,
    const char *key,
    unsigned char *output_block
);
```

- `input_block`：输入明文，必须正好 16 字节。
- `key`：正好 16 字节字符串 key。
- `output_block`：输出密文，调用方准备至少 16 字节。

示例：

```c
unsigned char out[16];
int rc = gm_sm4_ecb_encrypt_block(
    (const unsigned char *)"hello_world_1234",
    "hello_cinema_sm4",
    out
);
```

### 内存归属

- 所有输出都写入调用方传入的缓冲区。
- 调用方不需要也不应该对输出调用 `free()`。
- DLL 内部申请的 OpenSSL 上下文和临时缓冲区会在函数返回前释放。
- 如果返回 `GM_ERR_BUFFER_TOO_SMALL`，扩大输出缓冲区后重试。

## 3. LoadRunner 脚本用法

在 `vuser_init.c` 中加载 DLL：

```c
vuser_init()
{
    int rc = lr_load_dll("gm_crypto_x86.dll");
    if (rc != 0) {
        lr_error_message("load gm_crypto_x86.dll failed, rc=%d", rc);
        return -1;
    }
    return 0;
}
```

生成 SM3 签名：

```c
char payload[512];
char sm3_sign[65];
int rc;

sprintf(payload, "%s%s%s%s%s",
        lr_eval_string("{ShowtimeId}"),
        lr_eval_string("{SeatId}"),
        lr_eval_string("{Timestamp}"),
        lr_eval_string("{Nonce}"),
        "your_secret");

rc = gm_sm3_hex(payload, sm3_sign, sizeof(sm3_sign));
if (rc != 0) {
    lr_error_message("gm_sm3_hex failed, rc=%d", rc);
    return -1;
}

lr_save_string(sm3_sign, "SM3Signature");
web_add_header("X-Signature", "{SM3Signature}");
```

生成 SM4-CBC 加密密码，输出格式为 `IV_Hex + Cipher_Hex`：

```c
char plain[256];
char iv_hex[33];
char cipher_hex[1024];
char encrypted_password[1200];
int rc;

lr_save_timestamp("Timestamp", "DIGITS=13", LAST);
sprintf(plain, "%s:%s", lr_eval_string("{Timestamp}"), "123456");

rc = gm_sm4_cbc_encrypt_hex(
    plain,
    "hello_cinema_sm4", /* 16 字节 key */
    iv_hex,
    sizeof(iv_hex),
    cipher_hex,
    sizeof(cipher_hex)
);
if (rc != 0) {
    lr_error_message("gm_sm4_cbc_encrypt_hex failed, rc=%d", rc);
    return -1;
}

sprintf(encrypted_password, "%s%s", iv_hex, cipher_hex);
lr_save_string(encrypted_password, "EncryptedPassword");
```

如果 key 以 hex 形式配置，调用 `gm_sm4_cbc_encrypt_hex_key_hex`：

```c
rc = gm_sm4_cbc_encrypt_hex_key_hex(
    plain,
    "68656c6c6f5f63696e656d615f736d34",
    iv_hex,
    sizeof(iv_hex),
    cipher_hex,
    sizeof(cipher_hex)
);
```

## 4. WSL 交叉编译 32 位 DLL

LoadRunner 使用 32 位运行器时，需要编译 `i686` DLL。先安装工具链：

```bash
sudo apt update
sudo apt install mingw-w64 make perl curl tar unzip
```

### 方案 A：单体 DLL，静态链接 OpenSSL

这是部署最省事的方式：最终通常只需要把 `gm_crypto_x86.dll` 放到 LoadRunner 脚本目录。Windows 系统 DLL 仍然由系统提供，不会被静态打包。

下载并编译 32 位 OpenSSL 静态库：

```bash
OPENSSL_VERSION=3.3.2
curl -LO https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz
tar xf openssl-${OPENSSL_VERSION}.tar.gz
cd openssl-${OPENSSL_VERSION}

./Configure mingw no-shared no-tests no-module \
  --cross-compile-prefix=i686-w64-mingw32- \
  --prefix=$PWD/../openssl-mingw32-static

make -j"$(nproc)"
make install_sw
cd ..
```

编译 `gm_crypto_x86.dll`：

```bash
i686-w64-mingw32-gcc -O2 -Wall -Wextra -shared -static \
  -Iopenssl-mingw32-static/include \
  gm_crypto.c \
  -Lopenssl-mingw32-static/lib \
  -lcrypto -lws2_32 -lgdi32 -lcrypt32 -lbcrypt -ladvapi32 -luser32 \
  -o gm_crypto_x86.dll
```

检查依赖：

```bash
i686-w64-mingw32-objdump -p gm_crypto_x86.dll | grep 'DLL Name'
```

理想情况下不应出现 `libcrypto-*.dll`。如果看到 `libcrypto-3.dll`，说明链接到了动态 OpenSSL，不是单体 DLL。

### 方案 B：动态链接 OpenSSL

如果不追求单体 DLL，也可以链接动态 OpenSSL。部署时需要同时拷贝：

```text
gm_crypto_x86.dll
libcrypto-3.dll
```

动态链接方式取决于你的 OpenSSL 安装路径，示例：

```bash
i686-w64-mingw32-gcc -O2 -Wall -Wextra -shared \
  -Iopenssl-mingw32/include \
  gm_crypto.c \
  -Lopenssl-mingw32/lib \
  -lcrypto -lws2_32 -lgdi32 -lcrypt32 -lbcrypt -ladvapi32 -luser32 \
  -o gm_crypto_x86.dll
```

## 5. Windows 原生编译 DLL

如果不想在 WSL 里交叉编译，也可以直接在 Windows 上编译。轻量方案推荐 MSYS2 MinGW；Visual Studio 方案更重，适合已经安装 VS。

### 方案 A：MSYS2 MinGW，推荐轻量方案

安装 MSYS2 后，打开 `MSYS2 MinGW 32-bit` 或 `MSYS2 MinGW 64-bit` 终端。注意不要用普通 `MSYS` 终端。

32 位 LoadRunner 使用 `MINGW32` 终端：

```bash
pacman -Syu
pacman -S --needed mingw-w64-i686-gcc mingw-w64-i686-openssl
gcc -O2 -Wall -Wextra -shared gm_crypto.c \
  -lcrypto -lws2_32 -lgdi32 -lcrypt32 -lbcrypt -ladvapi32 -luser32 \
  -o gm_crypto_x86.dll
```

64 位 LoadRunner 使用 `MINGW64` 终端：

```bash
pacman -Syu
pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-openssl
gcc -O2 -Wall -Wextra -shared gm_crypto.c \
  -lcrypto -lws2_32 -lgdi32 -lcrypt32 -lbcrypt -ladvapi32 -luser32 \
  -o gm_crypto_x64.dll
```

MSYS2 默认通常是动态链接 OpenSSL。部署时需要把 DLL 依赖一起复制到 LoadRunner 脚本目录，常见依赖包括：

```text
gm_crypto_x86.dll
libcrypto-3.dll
libgcc_s_dw2-1.dll 或 libgcc_s_seh-1.dll
libwinpthread-1.dll
```

实际依赖以检查结果为准：

```bash
ntldd gm_crypto_x86.dll
```

如果没有 `ntldd`，可以安装：

```bash
pacman -S --needed mingw-w64-i686-ntldd
```

也可以用 Windows 自带或 VS 附带工具检查：

```bat
dumpbin /dependents gm_crypto_x86.dll
```

想减少 MinGW 运行时依赖，可以尝试：

```bash
gcc -O2 -Wall -Wextra -shared -static-libgcc gm_crypto.c \
  -lcrypto -lws2_32 -lgdi32 -lcrypt32 -lbcrypt -ladvapi32 -luser32 \
  -o gm_crypto_x86.dll
```

是否还能完全去掉 `libwinpthread-1.dll` 取决于 OpenSSL 包和链接方式，最终仍以 `ntldd`/`dumpbin` 为准。

### 方案 B：Visual Studio，重量级备选

如果机器已经安装 Visual Studio，也可以使用 `cl` 编译。推荐使用 OpenSSL 官方/可信渠道提供的 Windows 开发包，或自行用 Visual Studio 编译 OpenSSL。

#### 准备 OpenSSL

需要准备与 LoadRunner 位数一致的 OpenSSL：

- 32 位 LoadRunner：使用 32 位 OpenSSL，通常目录类似 `C:\OpenSSL-Win32`。
- 64 位 LoadRunner：使用 64 位 OpenSSL，通常目录类似 `C:\OpenSSL-Win64`。
- 头文件目录应包含 `openssl\evp.h`、`openssl\rand.h`、`openssl\crypto.h`。
- 库目录应包含 `libcrypto.lib`。

如果使用动态链接 OpenSSL，运行时还需要部署 `libcrypto-3.dll`。如果使用静态 OpenSSL，需要确保拿到的是静态版 `libcrypto.lib`，并按 OpenSSL 构建方式补齐系统库。

#### Visual Studio 命令行编译

打开对应位数的 Developer Command Prompt：

- 32 位 DLL：打开 `x86 Native Tools Command Prompt for VS`。
- 64 位 DLL：打开 `x64 Native Tools Command Prompt for VS`。

动态链接 OpenSSL 示例：

```bat
cl /O2 /LD /I C:\OpenSSL-Win32\include gm_crypto.c ^
  /link /LIBPATH:C:\OpenSSL-Win32\lib libcrypto.lib ^
  ws2_32.lib gdi32.lib crypt32.lib bcrypt.lib advapi32.lib user32.lib ^
  /OUT:gm_crypto_x86.dll
```

64 位时把路径和输出名换成：

```bat
cl /O2 /LD /I C:\OpenSSL-Win64\include gm_crypto.c ^
  /link /LIBPATH:C:\OpenSSL-Win64\lib libcrypto.lib ^
  ws2_32.lib gdi32.lib crypt32.lib bcrypt.lib advapi32.lib user32.lib ^
  /OUT:gm_crypto_x64.dll
```

#### Visual Studio 工程编译

也可以创建一个 `Dynamic-Link Library (DLL)` 工程：

- 将 `gm_crypto.c` 加入工程。
- `C/C++` -> `Additional Include Directories` 添加 OpenSSL 的 `include` 目录。
- `Linker` -> `Additional Library Directories` 添加 OpenSSL 的 `lib` 目录。
- `Linker` -> `Input` -> `Additional Dependencies` 添加 `libcrypto.lib;ws2_32.lib;gdi32.lib;crypt32.lib;bcrypt.lib;advapi32.lib;user32.lib`。
- `Configuration Manager` 选择 `Win32` 或 `x64`，必须与 LoadRunner 运行进程位数一致。

#### Windows 编译后的检查

检查 DLL 依赖：

```bat
dumpbin /dependents gm_crypto_x86.dll
```

如果看到 `libcrypto-3.dll`，部署时要把它和 `gm_crypto_x86.dll` 一起放到 LoadRunner 脚本目录，或放到系统 `PATH` 可搜索目录。

检查导出函数：

```bat
dumpbin /exports gm_crypto_x86.dll
```

应能看到 `gm_random_hex`、`gm_sm3_hex`、`gm_sm4_cbc_encrypt_hex` 等导出符号。

### Windows 下的选择建议

- 想工具轻量：优先 MSYS2 MinGW。
- 想部署简单：优先静态链接，生成尽量单体的 `gm_crypto_x86.dll`。
- 想编译简单：使用动态 OpenSSL，但部署时一起拷贝依赖 DLL。
- 不要混用位数：32 位 LoadRunner 不能加载 64 位 DLL，64 位 LoadRunner 也不能加载 32 位 DLL。
- 不要混用编译产物：`gm_crypto_x86.dll` 应链接 32 位 `libcrypto.lib`，`gm_crypto_x64.dll` 应链接 64 位 `libcrypto.lib`。

## 6. 64 位 DLL

如果 LoadRunner 运行器是 64 位，将 `i686-w64-mingw32-gcc` 换成 `x86_64-w64-mingw32-gcc`，OpenSSL 配置目标换成 `mingw64`：

```bash
./Configure mingw64 no-shared no-tests no-module \
  --cross-compile-prefix=x86_64-w64-mingw32- \
  --prefix=$PWD/../openssl-mingw64-static
```

## 7. 部署注意事项

- DLL 位数必须和 LoadRunner 运行进程一致，32 位脚本加载 64 位 DLL 会失败。
- 不要在 `Action()` 中反复 `lr_load_dll`，建议放在 `vuser_init()`。
- 所有 Load Generator 都要部署同版本 DLL。
- SM4 key 要么是 16 字节字符串，要么是 32 字符 hex；长度或字符非法会返回 `GM_ERR_PARAM`。
- 接口会检查输出缓冲区容量；容量不足会返回 `GM_ERR_BUFFER_TOO_SMALL`。
