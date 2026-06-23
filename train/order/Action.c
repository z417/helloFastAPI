Action() {
  int seatCounts; // 可选座位总数
  int index;
  char t_param_name[64];
  char *uid;
  char payload[512];
  char sm3_sign[65];
  char sha256_sign[65];
  char nonce[17];

  web_add_auto_header("Authorization", "Bearer {c_accessToken}");

  // 未来30天随机日期
  lr_save_datetime("%Y-%m-%d",
                   DATE_NOW + atoi(lr_eval_string("{p_randowDay}")) * 86400,
                   "p_filmDate");

  //	lr_output_message("目标日期: %s", lr_eval_string("{p_filmDate}"));

  web_reg_save_param_json("ParamName=c_showtimeUid",
                          "QueryString=$.data.showtimes[0].uid", SEARCH_FILTERS,
                          "Scope=BODY", LAST);

  web_url(
      "showtimes",
      "URL=http://172.24.17.1/api/cinema/"
      "showtimes?limit=1&offset={p_index}&date={p_filmDate}", // 随机分页(页大小为1)
      "Resource=0", "RecContentType=application/json",
      "Referer=http://172.24.17.1/", "Snapshot=t1.inf", "Mode=HTML", LAST);

  web_reg_save_param_json("ParamName=c_availableSeat",
                          "QueryString=$.data[?(@.status==0)].uid",
                          "SelectAll=Yes", LAST);

  web_url("seats",
          "URL=http://172.24.17.1/api/cinema/showtimes/{c_showtimeUid}/seats",
          "Resource=0", "RecContentType=application/json",
          "Referer=http://172.24.17.1/", "Snapshot=t2.inf", "Mode=HTML", LAST);

  seatCounts = atoi(lr_eval_string("{c_availableSeat_count}"));

  index = 1 + rand() % seatCounts;

  sprintf(t_param_name, "{c_availableSeat_%d}", index);

  uid = lr_eval_string(t_param_name);
  lr_save_string(uid, "c_selectedSeat");
  lr_save_timestamp("t_timestamp", "DIGITS=13", LAST);

  // 生成nonce
  gm_random_hex(nonce, sizeof(nonce), 8);

  // 拼接签名原文
  sprintf(payload, "%s%s%s%s%s", lr_eval_string("{c_showtimeUid}"),
          lr_eval_string("{c_selectedSeat}"), lr_eval_string("{t_timestamp}"),
          nonce, "hello_cinema_range_secret_key");

  // 计算sm3
  gm_sm3_hex(payload, sm3_sign, sizeof(sm3_sign));
  gm_sha256_hex(payload, sha256_sign, sizeof(sha256_sign));

  web_add_header("X-Timestamp", lr_eval_string("{t_timestamp}"));
  web_add_header("X-Nonce", nonce);
  web_add_header("X-Signature", sm3_sign);

  lr_save_string(sha256_sign, "p_sha256_sign");

  web_custom_request("order", "URL=http://172.24.17.1/api/cinema/order",
                     "Method=POST", "Resource=0",
                     "RecContentType=application/json",
                     "Referer=http://172.24.17.1/", "Snapshot=t4.inf",
                     "Mode=HTML", "EncType=application/json",
                     "Body={\"showtime_id\":\"{c_showtimeUid}\",\"seat_id\":\"{"
                     "c_selectedSeat}\",\"signature\":\"{p_sha256_sign}\"}",
                     LAST);

  return 0;
}