vuser_init() {
  int rc = lr_load_dll("gm_crypto_x86.dll");
  if (rc != 0) {
    lr_error_message("load gm_crypto_x86.dll failed, rc=%d", rc);
    return -1;
  }

  do_gm_sm4_cbc_encrypt_hex("123456");

  web_reg_save_param_json("ParamName=c_accessToken",
                          "QueryString=$.access_token", "NotFound=warning",
                          "SelectAll=No", SEARCH_FILTERS, "Scope=BODY", LAST);

  web_submit_data("token", "Action=http://172.24.17.1/api/auth/token",
                  "Method=POST", "RecContentType=application/json",
                  "Referer=http://172.24.17.1/", "Snapshot=t1.inf", "Mode=HTML",
                  "EncodeAtSign=YES", ITEMDATA, "Name=username",
                  "Value=user_{p_no}@test.com", ENDITEM, "Name=password",
                  "Value={EncryptedPassword}", ENDITEM, LAST);

  return 0;
}
