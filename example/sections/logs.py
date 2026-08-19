LOGS = {
    "data": [
        {
            "time": "2026-08-19 12:13:28.657",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Payment #10001 created payment_method:pse means_of_payment_type:wallet (wallet)",
        },
        {
            "time": "2026-08-19 12:13:28.672",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Headers: {&#x27;Host&#x27;: &#x27;api.example.test&#x27;, &#x27;X-Request-Id&#x27;: &#x27;req_REDACTED&#x27;, &#x27;X-Real-Ip&#x27;: &#x27;192.0.2.10&#x27;, &#x27;X-Forwarded-For&#x27;: &#x27;192.0.2.10&#x27;, &#x27;X-Forwarded-Host&#x27;: &#x27;api.example.test&#x27;, &#x27;X-Forwarded-Port&#x27;: &#x27;443&#x27;, &#x27;X-Forwarded-Proto&#x27;: &#x27;https&#x27;, &#x27;X-Forwarded-Scheme&#x27;: &#x27;https&#x27;, &#x27;X-Scheme&#x27;: &#x27;https&#x27;, &#x27;Content-Length&#x27;: &#x27;374&#x27;, &#x27;User-Agent&#x27;: &#x27;niquests/3.21.0&#x27;, &#x27;Accept-Encoding&#x27;: &#x27;gzip, deflate, br, zstd&#x27;, &#x27;Accept&#x27;: &#x27;application/json&#x27;, &#x27;Content-Type&#x27;: &#x27;application/json&#x27;, &#x27;Api-Sign&#x27;: &#x27;REDACTED_API_SIGN&#x27;}",
        },
        {
            "time": "2026-08-19 12:13:28.678",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Send callback (status:process endpoint:100)",
        },
        {
            "time": "2026-08-19 12:13:28.688",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_CALLBACK: Merchant #100 has no url for send &quot;notify&quot; callback",
        },
        {
            "time": "2026-08-19 12:13:28.691",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "GET_MEANS_OF_PAYMENT card_type:False number_type:None (is_h2h:True / is_p2p_card:False / mopt.code:wallet / number:None)",
        },
        {
            "time": "2026-08-19 12:13:28.695",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Means of payment created: False; Type: wallet (wallet);",
        },
        {
            "time": "2026-08-19 12:13:28.707",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Base filtering: Found endpoint_settings &lt;QuerySet [&lt;EndpointPaymentGatewaySettings: ID: 100; Endpoint id: 100 (examplePayment)&gt;]&gt;",
        },
        {
            "time": "2026-08-19 12:13:28.721",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Chaining: Found chains_settings &lt;QuerySet []&gt; for chaining",
        },
        {
            "time": "2026-08-19 12:13:28.743",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Chaining: Not found chains. Search base settings by system checking.",
        },
        {
            "time": "2026-08-19 12:13:28.746",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "CHECK_LIMITS: Found limits: &lt;QuerySet []&gt;",
        },
        {
            "time": "2026-08-19 12:13:28.750",
            "level": "<span style=\"color: Brown;\">warning</span>",
            "message": "CHECK_LIMITS COUNT: Found count limits: &lt;QuerySet []&gt;",
        },
        {
            "time": "2026-08-19 12:13:28.752",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "check_limit: True; check_limit_count: True; check_payout_limits: True",
        },
        {
            "time": "2026-08-19 12:13:28.754",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Chaining: Settings ID: 100; Endpoint id: 100 (examplePayment) passed limits: True",
        },
        {
            "time": "2026-08-19 12:13:28.759",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "ANTIFRAUD check tx #uuid_REDACTED provider: &quot;ExampleProvider&quot;",
        },
        {
            "time": "2026-08-19 12:13:28.765",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Chaining: Antifraud check chaining provider &quot;ExampleProvider&quot; result:True",
        },
        {
            "time": "2026-08-19 12:13:28.765",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Result of cls.chaining_settings(endpoint_settings, tx_data) = ID: 100; Endpoint id: 100 (examplePayment)",
        },
        {
            "time": "2026-08-19 12:13:28.768",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Settings #100 ID: 100; Endpoint id: 100 (examplePayment) selected (module:example).",
        },
        {
            "time": "2026-08-19 12:13:28.808",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "PAYMENT_SERVICE mark use_external_service=True integration:example",
        },
        {
            "time": "2026-08-19 12:13:30.900",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_REQUEST PaymentProvider POST<br>url:https://api.example.test/v1/counterparties<br>status_code:201<br>request_data:{&#x27;geo&#x27;: &#x27;col&#x27;, &#x27;type&#x27;: &#x27;r2p&#x27;, &#x27;metadata&#x27;: {&#x27;counterparty_fullname&#x27;: &#x27;Test User&#x27;, &#x27;counterparty_id_type&#x27;: &#x27;CC&#x27;, &#x27;counterparty_id_number&#x27;: &#x27;0000000000&#x27;, &#x27;counterparty_email&#x27;: &#x27;buyer@example.test&#x27;, &#x27;counterparty_phone&#x27;: &#x27;+570000000000&#x27;}}<br>request_headers:{&#x27;Content-Type&#x27;: &#x27;application/json&#x27;, &#x27;Authorization&#x27;: &#x27;Bearer REDACTED_TOKEN&#x27;}<br>response:{&quot;id&quot;:&quot;cp_REDACTED&quot;,&quot;geo&quot;:&quot;col&quot;,&quot;type&quot;:&quot;r2p&quot;,&quot;alias&quot;:null,&quot;metadata&quot;:{&quot;counterparty_id_type&quot;:&quot;cc&quot;,&quot;counterparty_id_number&quot;:&quot;0000000000&quot;,&quot;counterparty_email&quot;:&quot;buyer@example.test&quot;,&quot;counterparty_phone&quot;:&quot;+570000000000&quot;,&quot;counterparty_fullname&quot;:&quot;Test User&quot;},&quot;created_at&quot;:&quot;2026-08-18T06:24:41Z&quot;,&quot;updated_at&quot;:&quot;2026-08-18T06:24:41Z&quot;}<br>alt-svc:h3=&quot;:443&quot;; ma=93600<br>http_version:20",
        },
        {
            "time": "2026-08-19 12:13:32.404",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_REQUEST PaymentProvider POST<br>url:https://api.example.test/v1/test<br>status_code:201<br>request_data:{&#x27;source_id&#x27;: &#x27;cp_REDACTED&#x27;, &#x27;destination_id&#x27;: &#x27;acc_REDACTED&#x27;, &#x27;amount&#x27;: 1000, &#x27;metadata&#x27;: {&#x27;r2p_rail&#x27;: &#x27;pse&#x27;, &#x27;description_to_payer&#x27;: &#x27;Payment&#x27;, &#x27;description_to_payee&#x27;: &#x27;Payment&#x27;, &#x27;redirect_url&#x27;: &#x27;https://example.test/redirect/&#x27;, &#x27;financial_institution_code&#x27;: &#x27;507&#x27;}, &#x27;external_id&#x27;: &#x27;uuid_REDACTED&#x27;}<br>request_headers:{&#x27;Content-Type&#x27;: &#x27;application/json&#x27;, &#x27;Authorization&#x27;: &#x27;Bearer REDACTED_TOKEN&#x27;, &#x27;idempotency&#x27;: &#x27;uuid_REDACTED&#x27;}<br>response:{&quot;id&quot;:&quot;mm_REDACTED&quot;,&quot;status&quot;:{&quot;state&quot;:&quot;initiated&quot;,&quot;code&quot;:&quot;&quot;,&quot;description&quot;:&quot;&quot;},&quot;metadata&quot;:{&quot;financial_institution_code&quot;:&quot;507&quot;,&quot;description_to_payee&quot;:&quot;Payment&quot;,&quot;description_to_payer&quot;:&quot;Payment&quot;,&quot;r2p_rail&quot;:&quot;pse&quot;,&quot;redirect_url&quot;:&quot;https://example.test/redirect/&quot;},&quot;creator&quot;:&quot;cli_REDACTED&quot;,&quot;external_id&quot;:&quot;uuid_REDACTED&quot;,&quot;checker_approval&quot;:false,&quot;type&quot;:&quot;r2p_pse&quot;,&quot;geo&quot;:&quot;col&quot;,&quot;source_id&quot;:&quot;cp_REDACTED&quot;,&quot;destination_id&quot;:&quot;acc_REDACTED&quot;,&quot;currency&quot;:&quot;cop&quot;,&quot;amount&quot;:1000,&quot;created_at&quot;:&quot;2026-08-19T12:13:31Z&quot;}<br>alt-svc:h3=&quot;:443&quot;; ma=93600<br>http_version:20",
        },
        {
            "time": "2026-08-19 12:13:32.408",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "PAYMENT_SERVICE init result: RESULT(status_data:status=None error=None provider_status=None gateway_id=&#x27;mm_REDACTED&#x27; pan_mask=None new_amount=None check_status_after:False has_redirect:False has_tds:False has_qr_code:False has_card:False has_wallet:False)",
        },
        {
            "time": "2026-08-19 12:13:32.409",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Save gateway_id=mm_REDACTED",
        },
        {
            "time": "2026-08-19 12:13:32.421",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Amount changing = False: tx_status.new_amount=None",
        },
        {
            "time": "2026-08-19 12:13:32.440",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SAVE_PAYMENT_DATA: additional_data is saved to buyer: {}",
        },
        {
            "time": "2026-08-19 12:13:32.454",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "UPDATE_STATUS_AFTER_INIT check_status_after_init:False module:&lt;paymentgate.modules.module_controller.PaymentModuleController object at 0xREDACTED&gt; gateway_id:mm_REDACTED",
        },
        {
            "time": "2026-08-19 12:13:32.881",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "CALLBACK Get status from callback: TxStatus(status=&#x27;reversal&#x27;, gateway_id=&#x27;mm_REDACTED&#x27;, new_amount=1000)",
        },
        {
            "time": "2026-08-19 12:13:32.890",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Amount changing = False: tx_status.new_amount=1000",
        },
        {
            "time": "2026-08-19 12:13:32.927",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "UPDATE_STATUS: status updated (process to reversal) (need_send_callback:True)",
        },
        {
            "time": "2026-08-19 12:13:32.928",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Send callback (status:reversal endpoint:100)",
        },
        {
            "time": "2026-08-19 12:13:32.937",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_CALLBACK: Merchant #100 has no url for send &quot;notify&quot; callback",
        },
        {
            "time": "2026-08-19 12:13:32.945",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "get_transfer_module_type. ExamplePaymentModule tx:uuid_REDACTED card_payment:False payment_method:&quot;pse&quot; redirect_payment:False, p2p_wallet_payment:False, p2p_card:False, mopt_code:test_wallet",
        },
        {
            "time": "2026-08-19 12:13:33.174",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "CALLBACK Get status from callback: TxStatus(status=&#x27;process&#x27;, gateway_id=&#x27;mm_REDACTED&#x27;, new_amount=1000)",
        },
        {
            "time": "2026-08-19 12:13:33.182",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Amount changing = False: tx_status.new_amount=1000",
        },
        {
            "time": "2026-08-19 12:13:33.202",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "get_transfer_module_type. ExamplePaymentModule tx:uuid_REDACTED card_payment:False payment_method:&quot;pse&quot; redirect_payment:False, p2p_wallet_payment:False, p2p_card:False, mopt_code:test_wallet",
        },
        {
            "time": "2026-08-19 12:13:33.759",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_REQUEST PaymentProvider GetRequest<br>url:https://api.example.test/v1/test/mm_REDACTED<br>status_code:200<br>request_data:{}<br>request_headers:{&#x27;Content-Type&#x27;: &#x27;application/json&#x27;, &#x27;Authorization&#x27;: &#x27;Bearer REDACTED_TOKEN&#x27;}<br>response:{&quot;id&quot;:&quot;mm_REDACTED&quot;,&quot;batch_id&quot;:&quot;&quot;,&quot;external_id&quot;:&quot;uuid_REDACTED&quot;,&quot;creator&quot;:&quot;cli_REDACTED&quot;,&quot;type&quot;:&quot;r2p_pse&quot;,&quot;geo&quot;:&quot;col&quot;,&quot;status&quot;:{&quot;state&quot;:&quot;failed&quot;,&quot;code&quot;:&quot;F001&quot;,&quot;description&quot;:&quot;Payment processing failed please try again&quot;},&quot;source_id&quot;:&quot;cp_REDACTED&quot;,&quot;source&quot;:null,&quot;destination_id&quot;:&quot;acc_REDACTED&quot;,&quot;destination&quot;:null,&quot;currency&quot;:&quot;cop&quot;,&quot;amount&quot;:1000,&quot;metadata&quot;:{&quot;r2p_rail&quot;:&quot;pse&quot;,&quot;tracking_key&quot;:&quot;-1&quot;,&quot;payment_link&quot;:&quot;&quot;,&quot;description_to_payer&quot;:&quot;Payment&quot;,&quot;description_to_payee&quot;:&quot;Payment&quot;,&quot;redirect_url&quot;:&quot;https://example.test/redirect/&quot;,&quot;financial_institution_code&quot;:&quot;507&quot;,&quot;ticket_id&quot;:&quot;&quot;},&quot;checker_approval&quot;:false,&quot;mm_approval_id&quot;:&quot;&quot;,&quot;created_at&quot;:&quot;2026-08-19T12:13:31Z&quot;,&quot;updated_at&quot;:&quot;2026-08-19T12:13:32Z&quot;}<br>alt-svc:h3=&quot;:443&quot;; ma=93600<br>http_version:20",
        },
        {
            "time": "2026-08-19 12:13:33.767",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Amount changing = False: tx_status.new_amount=1000",
        },
        {
            "time": "2026-08-19 12:13:34.073",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "SEND_REQUEST PaymentProvider GetRequest<br>url:https://api.example.test/v1/test/mm_REDACTED<br>status_code:200<br>request_data:{}<br>request_headers:{&#x27;Content-Type&#x27;: &#x27;application/json&#x27;, &#x27;Authorization&#x27;: &#x27;Bearer REDACTED_TOKEN&#x27;}<br>response:{&quot;id&quot;:&quot;mm_REDACTED&quot;,&quot;batch_id&quot;:&quot;&quot;,&quot;external_id&quot;:&quot;uuid_REDACTED&quot;,&quot;creator&quot;:&quot;cli_REDACTED&quot;,&quot;type&quot;:&quot;r2p_pse&quot;,&quot;geo&quot;:&quot;col&quot;,&quot;status&quot;:{&quot;state&quot;:&quot;failed&quot;,&quot;code&quot;:&quot;F001&quot;,&quot;description&quot;:&quot;Payment processing failed please try again&quot;},&quot;source_id&quot;:&quot;cp_REDACTED&quot;,&quot;source&quot;:null,&quot;destination_id&quot;:&quot;acc_REDACTED&quot;,&quot;destination&quot;:null,&quot;currency&quot;:&quot;cop&quot;,&quot;amount&quot;:1000,&quot;metadata&quot;:{&quot;r2p_rail&quot;:&quot;pse&quot;,&quot;tracking_key&quot;:&quot;-1&quot;,&quot;payment_link&quot;:&quot;&quot;,&quot;description_to_payer&quot;:&quot;Payment&quot;,&quot;description_to_payee&quot;:&quot;Payment&quot;,&quot;redirect_url&quot;:&quot;https://example.test/redirect/&quot;,&quot;financial_institution_code&quot;:&quot;507&quot;,&quot;ticket_id&quot;:&quot;&quot;},&quot;checker_approval&quot;:false,&quot;mm_approval_id&quot;:&quot;&quot;,&quot;created_at&quot;:&quot;2026-08-19T12:13:31Z&quot;,&quot;updated_at&quot;:&quot;2026-08-19T12:13:32Z&quot;}<br>alt-svc:h3=&quot;:443&quot;; ma=93600<br>http_version:20",
        },
        {
            "time": "2026-08-19 12:13:34.080",
            "level": "<span style=\"color: Green;\">info</span>",
            "message": "Amount changing = False: tx_status.new_amount=1000",
        },
        {
            "time": "2026-08-19 12:13:52.923",
            "level": "<span style=\"color: Tomato;\">warning</span>",
            "message": "Card stat not send. Bank card not set",
        },
    ],
    "total_count": 40,
    "debug_info": None,
}
