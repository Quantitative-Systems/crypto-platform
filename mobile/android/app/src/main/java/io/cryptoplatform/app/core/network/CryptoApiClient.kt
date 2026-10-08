package io.cryptoplatform.app.core.network

import android.util.Log
import io.cryptoplatform.app.BuildConfig
import io.cryptoplatform.app.CryptoPlatformApp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

enum class NetworkStatus {
    CONNECTED,
    CONNECTING,
    DISCONNECTED,
    STALE_DATA
}

/**
 * High-performance OkHttp API client for Crypto Platform backend.
 * Handles authentication headers, timeouts, multi-tenancy, and fail-safe serialization.
 * Dynamically resolves environment endpoint (BuildConfig.BASE_URL or custom developer override).
 */
class CryptoApiClient(
    initialBaseUrl: String = BuildConfig.BASE_URL
) {
    private var baseUrl: String = try {
        CryptoPlatformApp.instance.secureStorage.customApiUrl ?: initialBaseUrl
    } catch (e: Exception) {
        initialBaseUrl
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    fun updateBaseUrl(newUrl: String) {
        baseUrl = newUrl.trimEnd('/')
        try {
            CryptoPlatformApp.instance.secureStorage.customApiUrl = baseUrl
        } catch (e: Exception) {
            Log.w("CryptoApiClient", "Failed to persist custom API URL: ${e.message}")
        }
    }

    fun getActiveBaseUrl(): String = baseUrl

    suspend fun get(path: String): Result<String> = withContext(Dispatchers.IO) {
        try {
            val storage = CryptoPlatformApp.instance.secureStorage
            val requestBuilder = Request.Builder()
                .url("$baseUrl$path")
                .header("Accept", "application/json")
                .header("X-Tenant-ID", storage.tenantId)

            storage.authToken?.let {
                requestBuilder.header("Authorization", "Bearer $it")
            }

            val response = client.newCall(requestBuilder.build()).execute()
            if (response.isSuccessful) {
                Result.success(response.body?.string().orEmpty())
            } else {
                Result.failure(IOException("HTTP ${response.code}: ${response.message}"))
            }
        } catch (e: Exception) {
            Log.w("CryptoApiClient", "GET $path failed: ${e.message}")
            Result.failure(e)
        }
    }

    suspend fun post(path: String, jsonBody: JSONObject): Result<String> = withContext(Dispatchers.IO) {
        try {
            val storage = CryptoPlatformApp.instance.secureStorage
            val body = jsonBody.toString().toRequestBody(jsonMediaType)
            val requestBuilder = Request.Builder()
                .url("$baseUrl$path")
                .post(body)
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .header("X-Tenant-ID", storage.tenantId)

            storage.authToken?.let {
                requestBuilder.header("Authorization", "Bearer $it")
            }

            val response = client.newCall(requestBuilder.build()).execute()
            if (response.isSuccessful) {
                Result.success(response.body?.string().orEmpty())
            } else {
                val errorBody = response.body?.string().orEmpty()
                Result.failure(IOException("HTTP ${response.code}: $errorBody"))
            }
        } catch (e: Exception) {
            Log.w("CryptoApiClient", "POST $path failed: ${e.message}")
            Result.failure(e)
        }
    }
}
