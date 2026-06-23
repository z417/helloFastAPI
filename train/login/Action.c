/**
 * 影城票务性能测试靶场 - 登录鉴权业务脚本
 */
Action() {
  // 1. 调用 globals.h 里的函数，将 "123456" 动态加密并注册为参数
  // {EncryptedPasswordParam}
  do_gm_sm4_cbc_encrypt_hex("123456");

  // 注册 JSON 解析器提取 Access Token
  web_reg_save_param_json("ParamName=c_accessToken",
                          "QueryString=$.access_token", "NotFound=warning",
                          "SelectAll=No", SEARCH_FILTERS, "Scope=BODY", LAST);

  lr_rendezvous("login");

  lr_start_transaction("login");

  /*Possible OAUTH authorization was detected. It is recommended to correlate
   * the authorization parameters.*/

  web_submit_data("token", "Action=http://172.24.17.1/api/auth/token",
                  "Method=POST", "RecContentType=application/json",
                  "Referer=http://172.24.17.1/", "Snapshot=t1.inf", "Mode=HTML",
                  "EncodeAtSign=YES", ITEMDATA, "Name=username",
                  "Value=user_{p_no}@test.com", ENDITEM, "Name=password",
                  "Value={EncryptedPassword}", ENDITEM, LAST);

  lr_end_transaction("login", LR_AUTO);

  return 0;
}