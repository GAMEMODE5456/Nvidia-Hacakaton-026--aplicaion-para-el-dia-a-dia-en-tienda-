package com.example.donnacho
import android.annotation.SuppressLint
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.stripe.stripeterminal.Terminal
import com.stripe.stripeterminal.external.callable.Callback
import com.stripe.stripeterminal.external.callable.DiscoveryListener
import com.stripe.stripeterminal.external.callable.MobileReaderListener
import com.stripe.stripeterminal.external.callable.PaymentIntentCallback
import com.stripe.stripeterminal.external.callable.ReaderCallback
import com.stripe.stripeterminal.external.models.CollectPaymentIntentConfiguration
import com.stripe.stripeterminal.external.models.ConfirmPaymentIntentConfiguration
import com.stripe.stripeterminal.external.models.ConnectionConfiguration.BluetoothConnectionConfiguration
import com.stripe.stripeterminal.external.models.DiscoveryConfiguration.BluetoothDiscoveryConfiguration
import com.stripe.stripeterminal.external.models.PaymentIntent
import com.stripe.stripeterminal.external.models.Reader
import com.stripe.stripeterminal.external.models.ReaderDisplayMessage
import com.stripe.stripeterminal.external.models.ReaderInputOptions
import com.stripe.stripeterminal.external.models.TerminalException
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

typealias PayDone = (status: String, paymentIntentId: String?, message: String?) -> Unit

object TerminalPayments {

    private const val TAG = "TERMINAL"
    private var connecting = false

    private val readerListener = object : MobileReaderListener {
        override fun onRequestReaderInput(options: ReaderInputOptions) {
            Log.d(TAG, "lector pide: $options")
        }

        override fun onRequestReaderDisplayMessage(message: ReaderDisplayMessage) {
            Log.d(TAG, "lector dice: $message")
        }
    }

    /** Punto de entrada: conecta el lector si hace falta y cobra. */
    fun pay(amountCents: Int, done: PayDone) {
        if (!Terminal.isInitialized()) {
            done("failed", null, "Terminal de pago no inicializado. Reinicia la app.")
            return
        }
        ensureReader(
            onReady = { crearCobro(amountCents, done) },
            onError = { done("failed", null, it) }
        )
    }

    @SuppressLint("MissingPermission")
    private fun ensureReader(onReady: () -> Unit, onError: (String) -> Unit) {
        val terminal = Terminal.getInstance()
        if (terminal.connectedReader != null) {
            onReady()
            return
        }
        if (connecting) {
            onError("Conectando el lector, intenta de nuevo en unos segundos.")
            return
        }
        connecting = true

        val config = BluetoothDiscoveryConfiguration(timeout = 0, isSimulated = true)
        var connectStarted = false

        terminal.discoverReaders(
            config,
            object : DiscoveryListener {
                override fun onUpdateDiscoveredReaders(readers: List<Reader>) {
                    if (connectStarted || readers.isEmpty()) return
                    connectStarted = true
                    val reader = readers.first()
                    val connConfig = BluetoothConnectionConfiguration(
                        locationId = reader.location?.id.orEmpty(),
                        autoReconnectOnUnexpectedDisconnect = true,
                        bluetoothReaderListener = readerListener
                    )
                    terminal.connectReader(reader, connConfig, object : ReaderCallback {
                        override fun onSuccess(reader: Reader) {
                            connecting = false
                            Log.d(TAG, "Lector conectado: ${reader.label ?: reader.serialNumber}")
                            onReady()
                        }

                        override fun onFailure(e: TerminalException) {
                            connecting = false
                            Log.e(TAG, "connectReader falló: ${e.message}")
                            onError("No se pudo conectar el lector: ${e.message}")
                        }
                    })
                }
            },
            object : Callback {
                override fun onSuccess() {}
                override fun onFailure(e: TerminalException) {
                    if (!connectStarted) {
                        connecting = false
                        Log.e(TAG, "discoverReaders falló: ${e.message}")
                        onError("No se encontró el lector: ${e.message}")
                    }
                }
            }
        )
    }

    /** Pide a tu backend que cree el PaymentIntent y devuelva el client_secret. */
    private fun crearCobro(amountCents: Int, done: PayDone) {
        thread {
            try {
                val conn = URL(Config.BACKEND_URL + "/create_payment_intent")
                    .openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("ngrok-skip-browser-warning", "1")
                conn.outputStream.use {
                    it.write(JSONObject().put("amount", amountCents).toString().toByteArray())
                }
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                val secret = JSONObject(body).getString("client_secret")
                Handler(Looper.getMainLooper()).post { cobrar(secret, done) }
            } catch (e: Exception) {
                Log.e(TAG, "create_payment_intent falló", e)
                done("failed", null, "No se pudo crear el cobro: ${e.message}")
            }
        }
    }

    /** Trae el PaymentIntent y lo procesa con el lector (collect + confirm en un paso). */
    private fun cobrar(clientSecret: String, done: PayDone) {
        Terminal.getInstance().retrievePaymentIntent(
            clientSecret,
            object : PaymentIntentCallback {
                override fun onSuccess(paymentIntent: PaymentIntent) {
                    Terminal.getInstance().processPaymentIntent(
                        intent = paymentIntent,
                        collectConfig = CollectPaymentIntentConfiguration.Builder().build(),
                        confirmConfig = ConfirmPaymentIntentConfiguration.Builder().build(),
                        callback = object : PaymentIntentCallback {
                            override fun onSuccess(paymentIntent: PaymentIntent) {
                                Log.d(TAG, "Pago procesado: ${paymentIntent.id}")
                                done("succeeded", paymentIntent.id, null)
                            }

                            override fun onFailure(e: TerminalException) {
                                Log.e(TAG, "processPaymentIntent falló: ${e.message}")
                                done("failed", null, "Pago no completado: ${e.message}")
                            }
                        }
                    )
                }

                override fun onFailure(e: TerminalException) {
                    Log.e(TAG, "retrievePaymentIntent falló: ${e.message}")
                    done("failed", null, "No se pudo leer el cobro: ${e.message}")
                }
            }
        )
    }
}