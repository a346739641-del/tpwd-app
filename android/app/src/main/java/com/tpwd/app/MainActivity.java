package com.tpwd.app;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.JsPromptResult;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.view.KeyEvent;
import androidx.appcompat.app.AppCompatActivity;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private static final String API_URL = "https://flask-nim9-269824-9-1442901802.sh.run.tcloudbase.com/parse";
    private Handler mainHandler = new Handler(Looper.getMainLooper());

    private String getClipText() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm.hasPrimaryClip()) {
            ClipData cd = cm.getPrimaryClip();
            if (cd != null && cd.getItemCount() > 0) {
                CharSequence text = cd.getItemAt(0).getText();
                return text != null ? text.toString() : "";
            }
        }
        return "";
    }

    private void setClipText(String text) {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("label", text));
    }

    public class ApiBridge {
        @JavascriptInterface
        public void callApi(final String content) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    final String result = doHttpPost(content);
                    mainHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            webView.evaluateJavascript("window.__apiResult(" + result + ")", null);
                        }
                    });
                }
            }).start();
        }
    }

    private String doHttpPost(String content) {
        try {
            URL url = new URL(API_URL);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
            conn.setDoOutput(true);
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);
            byte[] body = ("content=" + java.net.URLEncoder.encode(content, "UTF-8")).getBytes(StandardCharsets.UTF_8);
            conn.setFixedLengthStreamingMode(body.length);
            OutputStream os = conn.getOutputStream();
            os.write(body);
            os.close();
            java.io.InputStream is = conn.getResponseCode() == 200 ? conn.getInputStream() : conn.getErrorStream();
            java.util.Scanner s = new java.util.Scanner(is, "UTF-8").useDelimiter("\\A");
            return s.hasNext() ? s.next() : "{\"code\":1,\"msg\":\"empty response\"}";
        } catch (Exception e) {
            return "{\"code\":1,\"msg\":\"" + e.getClass().getSimpleName() + ": " + e.getMessage() + "\"}";
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);

        webView.addJavascriptInterface(new ApiBridge(), "TpwdApp");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
                if ("CLIPBOARD_GET".equals(message)) {
                    result.confirm(getClipText());
                    return true;
                }
                if ("CLIPBOARD_SET".equals(message)) {
                    setClipText(defaultValue);
                    result.confirm("");
                    return true;
                }
                return super.onJsPrompt(view, url, message, defaultValue, result);
            }
        });
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
