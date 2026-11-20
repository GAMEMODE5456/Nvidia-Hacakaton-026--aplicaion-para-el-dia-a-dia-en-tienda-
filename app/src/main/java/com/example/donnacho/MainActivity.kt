package com.example.donnacho

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.webkit.ConsoleMessage
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.stripe.stripeterminal.Terminal
import com.stripe.stripeterminal.external.callable.TerminalListener
import com.stripe.stripeterminal.external.models.ConnectionStatus
import com.stripe.stripeterminal.external.models.LocaleConfig
import com.stripe.stripeterminal.external.models.PaymentStatus
import com.stripe.stripeterminal.log.LogLevel
import org.json.JSONObject

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var pendingRequest: PermissionRequest? = null

    private val camPerm = registerForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        pendingRequest?.let { if (ok) it.grant(it.resources) else it.deny() }
        pendingRequest = null
    }

    private val permsLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.mediaPlaybackRequiresUserGesture = false
        webView.settings.cacheMode = WebSettings.LOAD_NO_CACHE
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    pendingRequest = request
                    camPerm.launch(Manifest.permission.CAMERA)
                }
            }

            override fun onConsoleMessage(m: ConsoleMessage): Boolean {
                Log.d("WEB", "${m.message()} (${m.sourceId()}:${m.lineNumber()})")
                return true
            }
        }

        webView.addJavascriptInterface(PaymentBridge(), "Android")
        webView.loadUrl("https://geovani5410.github.io/Abarrotes-Don-Nacho/")

        pedirPermisosTerminal()
        initTerminal()
    }
    private fun pedirPermisosTerminal() {
        val faltan = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT
        ).filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (faltan.isNotEmpty()) permsLauncher.launch(faltan.toTypedArray())
    }
    private fun initTerminal() {
        if (Terminal.isInitialized()) return
        val listener = object : TerminalListener {
            override fun onConnectionStatusChange(status: ConnectionStatus) {
                Log.d("TERMINAL", "conexión: $status")
            }

            override fun onPaymentStatusChange(status: PaymentStatus) {
                Log.d("TERMINAL", "pago: $status")
            }
        }

        Terminal.init(
            applicationContext, LogLevel.VERBOSE, BackendTokenProvider(),
            listener, null, LocaleConfig.CardLanguagePreferenceIfAvailable
        )
    }

    private fun sendResult(status: String, id: String?, message: String?) {
        val json = JSONObject()
            .put("status", status)
            .put("paymentIntentId", id)
            .put("message", message)
        runOnUiThread { webView.evaluateJavascript("window.onPaymentResult($json)", null) }
    }

    inner class PaymentBridge {
        @JavascriptInterface
        fun startPayment(amountCents: Int) {
            runOnUiThread {
                TerminalPayments.pay(amountCents) { status, id, message ->
                    sendResult(status, id, message)
                }
            }
        }
    }
}