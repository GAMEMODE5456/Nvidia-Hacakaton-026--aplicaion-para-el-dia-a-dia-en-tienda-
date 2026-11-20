package com.example.donnacho

import com.stripe.stripeterminal.external.callable.ConnectionTokenCallback
import com.stripe.stripeterminal.external.callable.ConnectionTokenProvider
import com.stripe.stripeterminal.external.models.ConnectionTokenException
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

object Config {
    const val BACKEND_URL = "https://populate-conductor-coastline.ngrok-free.dev"
}

class BackendTokenProvider : ConnectionTokenProvider {
    override fun fetchConnectionToken(callback: ConnectionTokenCallback) {
        thread {
            try {
                val conn = URL(Config.BACKEND_URL + "/connection_token")
                    .openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("ngrok-skip-browser-warning", "1")
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                callback.onSuccess(JSONObject(body).getString("secret"))
            } catch (e: Exception) {
                callback.onFailure(ConnectionTokenException("No se pudo obtener el token", e))
            }
        }
    }
}