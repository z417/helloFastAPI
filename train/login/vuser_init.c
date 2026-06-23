vuser_init() {
  int rc = lr_load_dll("gm_crypto_x86.dll");
  if (rc != 0) {
    lr_error_message("load gm_crypto_x86.dll failed, rc=%d", rc);
    return -1;
  }
  return 0;
}
