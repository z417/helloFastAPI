#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT __attribute__((visibility("default")))
#endif

#define GM_OK 0
#define GM_ERR_PARAM -1
#define GM_ERR_BUFFER_TOO_SMALL -2
#define GM_ERR_CRYPTO -3
#define GM_ERR_UNSUPPORTED -4

static const char HEX_CHARS[] = "0123456789abcdef";

static int hex_encode(const unsigned char *input, size_t input_len, char *output, size_t output_cap)
{
    size_t i;

    if (input == NULL || output == NULL) {
        return GM_ERR_PARAM;
    }
    if (input_len > (SIZE_MAX - 1) / 2 || output_cap < input_len * 2 + 1) {
        return GM_ERR_BUFFER_TOO_SMALL;
    }

    for (i = 0; i < input_len; i++) {
        output[i * 2] = HEX_CHARS[input[i] >> 4];
        output[i * 2 + 1] = HEX_CHARS[input[i] & 0x0f];
    }
    output[input_len * 2] = '\0';

    return GM_OK;
}

static int hex_value(char value)
{
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    if (value >= 'A' && value <= 'F') {
        return value - 'A' + 10;
    }
    return -1;
}

static int hex_decode_exact(const char *input_hex, unsigned char *output, size_t output_len)
{
    size_t i;

    if (input_hex == NULL || output == NULL) {
        return GM_ERR_PARAM;
    }
    if (strlen(input_hex) != output_len * 2) {
        return GM_ERR_PARAM;
    }

    for (i = 0; i < output_len; i++) {
        int high = hex_value(input_hex[i * 2]);
        int low = hex_value(input_hex[i * 2 + 1]);
        if (high < 0 || low < 0) {
            return GM_ERR_PARAM;
        }
        output[i] = (unsigned char)((high << 4) | low);
    }

    return GM_OK;
}

static int copy_sm4_key_bytes(const char *key, unsigned char raw_key[16])
{
    size_t key_len;

    if (key == NULL) {
        return GM_ERR_PARAM;
    }

    key_len = strlen(key);
    if (key_len != 16) {
        return GM_ERR_PARAM;
    }

    memcpy(raw_key, key, 16);
    return GM_OK;
}

static int copy_sm4_key_hex(const char *key_hex, unsigned char raw_key[16])
{
    return hex_decode_exact(key_hex, raw_key, 16);
}

static int digest_hex(const EVP_MD *digest_type, const char *input, char *output_hex, size_t output_cap)
{
    EVP_MD_CTX *ctx;
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    int result = GM_ERR_CRYPTO;

    if (digest_type == NULL || input == NULL || output_hex == NULL) {
        return GM_ERR_PARAM;
    }

    ctx = EVP_MD_CTX_new();
    if (ctx == NULL) {
        return GM_ERR_CRYPTO;
    }

    if (EVP_DigestInit_ex(ctx, digest_type, NULL) != 1) {
        goto cleanup;
    }
    if (EVP_DigestUpdate(ctx, input, strlen(input)) != 1) {
        goto cleanup;
    }
    if (EVP_DigestFinal_ex(ctx, digest, &digest_len) != 1) {
        goto cleanup;
    }

    result = hex_encode(digest, digest_len, output_hex, output_cap);

cleanup:
    EVP_MD_CTX_free(ctx);
    return result;
}

DLL_EXPORT int gm_random_hex(char *output_hex, int output_cap, int byte_len)
{
    unsigned char random_bytes[64];
    int result;

    if (output_hex == NULL || output_cap <= 0 || byte_len <= 0) {
        return GM_ERR_PARAM;
    }
    if (byte_len > (int)sizeof(random_bytes)) {
        return GM_ERR_PARAM;
    }
    if (output_cap < byte_len * 2 + 1) {
        return GM_ERR_BUFFER_TOO_SMALL;
    }
    if (RAND_bytes(random_bytes, byte_len) != 1) {
        return GM_ERR_CRYPTO;
    }

    result = hex_encode(random_bytes, (size_t)byte_len, output_hex, (size_t)output_cap);
    OPENSSL_cleanse(random_bytes, sizeof(random_bytes));
    return result;
}

DLL_EXPORT int gm_sha256_hex(const char *input, char *output_hex, int output_cap)
{
    if (output_cap <= 0) {
        return GM_ERR_PARAM;
    }
    return digest_hex(EVP_sha256(), input, output_hex, (size_t)output_cap);
}

DLL_EXPORT int gm_sm3_hex(const char *input, char *output_hex, int output_cap)
{
    if (output_cap <= 0) {
        return GM_ERR_PARAM;
    }
    return digest_hex(EVP_sm3(), input, output_hex, (size_t)output_cap);
}

static int sm4_cbc_encrypt_hex_with_key(const char *plain, const char *iv_hex, const unsigned char raw_key[16],
                                        char *output_hex, int output_cap)
{
    EVP_CIPHER_CTX *ctx;
    unsigned char iv[16];
    int plain_len;
    int max_cipher_len;
    int len = 0;
    int cipher_len = 0;
    int result = GM_ERR_CRYPTO;
    size_t max_output_len;
    unsigned char *cipher_buf = NULL;

    if (plain == NULL || iv_hex == NULL || raw_key == NULL || output_hex == NULL || output_cap <= 0) {
        return GM_ERR_PARAM;
    }
    if (hex_decode_exact(iv_hex, iv, sizeof(iv)) != GM_OK) {
        return GM_ERR_PARAM;
    }
    if (strlen(plain) > (size_t)(INT_MAX - EVP_MAX_BLOCK_LENGTH)) {
        return GM_ERR_PARAM;
    }

    plain_len = (int)strlen(plain);
    max_cipher_len = plain_len + EVP_MAX_BLOCK_LENGTH;
    max_output_len = (size_t)max_cipher_len * 2 + 1;
    if ((size_t)output_cap < max_output_len) {
        return GM_ERR_BUFFER_TOO_SMALL;
    }

    cipher_buf = OPENSSL_malloc((size_t)max_cipher_len);
    ctx = EVP_CIPHER_CTX_new();
    if (cipher_buf == NULL || ctx == NULL) {
        goto cleanup;
    }

    if (EVP_EncryptInit_ex(ctx, EVP_sm4_cbc(), NULL, raw_key, iv) != 1) {
        goto cleanup;
    }
    if (EVP_EncryptUpdate(ctx, cipher_buf, &len, (const unsigned char *)plain, plain_len) != 1) {
        goto cleanup;
    }
    cipher_len = len;
    if (EVP_EncryptFinal_ex(ctx, cipher_buf + cipher_len, &len) != 1) {
        goto cleanup;
    }
    cipher_len += len;

    result = hex_encode(cipher_buf, (size_t)cipher_len, output_hex, (size_t)output_cap);

cleanup:
    if (ctx != NULL) {
        EVP_CIPHER_CTX_free(ctx);
    }
    if (cipher_buf != NULL) {
        OPENSSL_clear_free(cipher_buf, (size_t)max_cipher_len);
    }
    OPENSSL_cleanse(iv, sizeof(iv));
    return result;
}

DLL_EXPORT int gm_sm4_cbc_encrypt_hex_with_iv(const char *plain, const char *iv_hex, const char *key,
                                               char *output_hex, int output_cap)
{
    unsigned char raw_key[16];
    int result;

    result = copy_sm4_key_bytes(key, raw_key);
    if (result != GM_OK) {
        return result;
    }

    result = sm4_cbc_encrypt_hex_with_key(plain, iv_hex, raw_key, output_hex, output_cap);
    OPENSSL_cleanse(raw_key, sizeof(raw_key));
    return result;
}

DLL_EXPORT int gm_sm4_cbc_encrypt_hex_with_iv_key_hex(const char *plain, const char *iv_hex, const char *key_hex,
                                                       char *output_hex, int output_cap)
{
    unsigned char raw_key[16];
    int result;

    result = copy_sm4_key_hex(key_hex, raw_key);
    if (result != GM_OK) {
        return result;
    }

    result = sm4_cbc_encrypt_hex_with_key(plain, iv_hex, raw_key, output_hex, output_cap);
    OPENSSL_cleanse(raw_key, sizeof(raw_key));
    return result;
}

DLL_EXPORT int gm_sm4_cbc_encrypt_hex(const char *plain, const char *key,
                                      char *output_iv_hex, int iv_cap,
                                      char *output_cipher_hex, int cipher_cap)
{
    int result;

    if (output_iv_hex == NULL || iv_cap <= 0) {
        return GM_ERR_PARAM;
    }

    result = gm_random_hex(output_iv_hex, iv_cap, 16);
    if (result != GM_OK) {
        return result;
    }

    return gm_sm4_cbc_encrypt_hex_with_iv(plain, output_iv_hex, key, output_cipher_hex, cipher_cap);
}

DLL_EXPORT int gm_sm4_cbc_encrypt_hex_key_hex(const char *plain, const char *key_hex,
                                              char *output_iv_hex, int iv_cap,
                                              char *output_cipher_hex, int cipher_cap)
{
    int result;

    if (output_iv_hex == NULL || iv_cap <= 0) {
        return GM_ERR_PARAM;
    }

    result = gm_random_hex(output_iv_hex, iv_cap, 16);
    if (result != GM_OK) {
        return result;
    }

    return gm_sm4_cbc_encrypt_hex_with_iv_key_hex(plain, output_iv_hex, key_hex, output_cipher_hex, cipher_cap);
}

DLL_EXPORT int gm_sm4_ecb_encrypt_block(const unsigned char *input_block, const char *key, unsigned char *output_block)
{
    EVP_CIPHER_CTX *ctx;
    unsigned char raw_key[16];
    int len = 0;
    int result = GM_ERR_CRYPTO;

    if (input_block == NULL || output_block == NULL) {
        return GM_ERR_PARAM;
    }
    if (copy_sm4_key_bytes(key, raw_key) != GM_OK) {
        return GM_ERR_PARAM;
    }

    ctx = EVP_CIPHER_CTX_new();
    if (ctx == NULL) {
        OPENSSL_cleanse(raw_key, sizeof(raw_key));
        return GM_ERR_CRYPTO;
    }

    if (EVP_EncryptInit_ex(ctx, EVP_sm4_ecb(), NULL, raw_key, NULL) != 1) {
        goto cleanup;
    }
    EVP_CIPHER_CTX_set_padding(ctx, 0);
    if (EVP_EncryptUpdate(ctx, output_block, &len, input_block, 16) != 1 || len != 16) {
        goto cleanup;
    }
    if (EVP_EncryptFinal_ex(ctx, output_block + len, &len) != 1 || len != 0) {
        goto cleanup;
    }

    result = GM_OK;

cleanup:
    EVP_CIPHER_CTX_free(ctx);
    OPENSSL_cleanse(raw_key, sizeof(raw_key));
    return result;
}
