package io.cryptoplatform.app;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

/**
 * Main Activity for Crypto Platform Android Application.
 * Host WebView container executing the financial trading and quantitative research interface.
 */
public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private WebAppInterface webAppInterface;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        
        // Strict security configurations
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webAppInterface = new WebAppInterface(this);
        webView.addJavascriptInterface(webAppInterface, "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Keep navigation internal to application
                return false;
            }
        });

        // Safe back press dispatcher
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });

        // Load primary asset
        webView.loadUrl("file:///android_asset/www/index.html");
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) {
            webView.onPause();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
