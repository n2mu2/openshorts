package com.openshorts.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.openshorts.app.ui.nav.AppNav
import com.openshorts.app.ui.theme.OpenShortsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            OpenShortsTheme {
                AppNav()
            }
        }
    }
}
