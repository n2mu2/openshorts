package com.openshorts.app

import android.app.Application
import com.openshorts.app.core.prefs.AppSettings
import com.openshorts.app.core.prefs.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class OpenShortsApp : Application() {

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val _settings = MutableStateFlow(AppSettings())
    val settings: StateFlow<AppSettings> = _settings.asStateFlow()

    override fun onCreate() {
        super.onCreate()
        SettingsStore.init(this)
        appScope.launch {
            SettingsStore.settings.collect { _settings.value = it }
        }
    }
}
