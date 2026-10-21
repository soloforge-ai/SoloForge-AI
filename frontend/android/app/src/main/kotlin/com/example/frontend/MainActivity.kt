package com.example.frontend

import android.content.ContentValues
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "soloforge.ai/gallery")
            .setMethodCallHandler { call, result ->
                if (call.method != "saveImage") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
                    result.error("UNSUPPORTED", "Direct Gallery save requires Android 10 or newer.", null)
                    return@setMethodCallHandler
                }
                val bytes = call.argument<ByteArray>("bytes")
                val fileName = call.argument<String>("fileName")
                val mimeType = call.argument<String>("mimeType")
                if (bytes == null || bytes.isEmpty() ||
                    fileName == null || !Regex("^soloforge-[a-zA-Z0-9_-]+\\.(png|jpg)$").matches(fileName) ||
                    (mimeType != "image/png" && mimeType != "image/jpeg") ||
                    !fileName.endsWith(if (mimeType == "image/png") ".png" else ".jpg")) {
                    result.error("INVALID_IMAGE", "Invalid image export request.", null)
                    return@setMethodCallHandler
                }
                val resolver = applicationContext.contentResolver
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                    put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                    put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/SoloForge")
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
                var uri: android.net.Uri? = null
                try {
                    uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                        ?: throw IllegalStateException("Gallery could not create an image.")
                    resolver.openOutputStream(uri)?.use { it.write(bytes) }
                        ?: throw IllegalStateException("Gallery could not write the image.")
                    val ready = ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
                    if (resolver.update(uri, ready, null, null) < 1) {
                        throw IllegalStateException("Gallery could not finalize the image.")
                    }
                    result.success(true)
                } catch (error: Exception) {
                    uri?.let { resolver.delete(it, null, null) }
                    result.error("SAVE_FAILED", "Could not save image to Gallery.", null)
                }
            }
    }
}
