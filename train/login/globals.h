#ifndef _GLOBALS_H
#define _GLOBALS_H

//--------------------------------------------------------------------
// Include Files
#include "lrun.h"
#include "lrw_custom_body.h"
#include "web_api.h"

// 1. 声明外部 DLL 加密接口
extern int gm_sm4_cbc_encrypt_hex(const char *plain, const char *key,
                                  char *out_iv_hex, int iv_cap,
                                  char *out_cipher_hex, int cipher_cap);

// 2. 封装加密辅助函数 (入参为明文密码，计算后直接写入 LoadRunner 变量池)
void do_gm_sm4_cbc_encrypt_hex(const char *plain_pwd) {
  char plain[256];
  char iv_hex[33];
  char cipher_hex[1024];
  char encrypted_password[1200];
  char *sm4_key = "hello_cinema_sm4"; // 后端配置的 16 字节 SM4 Key

  lr_save_timestamp("Timestamp", "DIGITS=13", LAST);

  // 拼接明文负载: "时间戳:明文密码"
  sprintf(plain, "%s:%s", lr_eval_string("{Timestamp}"), plain_pwd);

  // 执行 SM4 CBC 加密并输出密文 Hex
  gm_sm4_cbc_encrypt_hex(plain, sm4_key, iv_hex, sizeof(iv_hex), cipher_hex,
                         sizeof(cipher_hex));
  // 物理拼接: IV_Hex + Cipher_Hex
  sprintf(encrypted_password, "%s%s", iv_hex, cipher_hex);
  // 将最终密文存入 LoadRunner 参数，命名为 {EncryptedPassword}
  lr_save_string(encrypted_password, "EncryptedPassword");
}

//--------------------------------------------------------------------
// Global Variables
#endif // _GLOBALS_H