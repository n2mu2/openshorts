package com.openshorts.app.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.openshorts.app.core.prefs.StoredJob
import com.openshorts.app.ui.clips.ClipGeneratorScreen
import com.openshorts.app.ui.home.HomeScreen
import com.openshorts.app.ui.settings.SettingsScreen
import com.openshorts.app.ui.shorts.AiShortsScreen
import com.openshorts.app.ui.social.SocialScreen
import com.openshorts.app.ui.theme.Brass
import com.openshorts.app.ui.theme.InkSurface
import com.openshorts.app.ui.theme.Hairline
import com.openshorts.app.ui.theme.TextSecondary

private data class NavItem(
    val route: String,
    val label: String,
    val icon: ImageVector,
)

private val NAV_ITEMS = listOf(
    NavItem("home", "Home", Icons.Default.Home),
    NavItem("shorts", "AI Shorts", Icons.Default.Star),
    NavItem("clips", "Clips", Icons.Default.PlayArrow),
    NavItem("social", "Social", Icons.Default.Share),
    NavItem("settings", "Settings", Icons.Default.Settings),
)

@Composable
fun AppNav() {
    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route ?: "home"

    Scaffold(
        containerColor = androidx.compose.ui.graphics.Color(0xFF0E0B14),
        bottomBar = {
            NavigationBar(containerColor = InkSurface) {
                NAV_ITEMS.forEach { item ->
                    val selected = currentRoute.substringBefore("?") == item.route
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            nav.navigate(item.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(item.icon, contentDescription = item.label) },
                        label = { Text(item.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Brass,
                            selectedTextColor = Brass,
                            indicatorColor = Hairline,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                        ),
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = nav,
            startDestination = "home",
            modifier = Modifier.padding(padding),
        ) {
            composable("home") {
                HomeScreen(
                    onNewShort = { nav.navigate("shorts") },
                    onNewClip = { nav.navigate("clips") },
                    onOpenJob = { job: StoredJob -> openJob(nav, job) },
                )
            }
            composable(
                route = "shorts?jobId={jobId}",
                arguments = listOf(
                    navArgument("jobId") {
                        type = NavType.StringType
                        defaultValue = ""
                    }
                ),
            ) { entry ->
                val jobId = entry.arguments?.getString("jobId").orEmpty()
                AiShortsScreen(jobId = jobId.ifBlank { null })
            }
            composable(
                route = "clips?jobId={jobId}",
                arguments = listOf(
                    navArgument("jobId") {
                        type = NavType.StringType
                        defaultValue = ""
                    }
                ),
            ) { entry ->
                val jobId = entry.arguments?.getString("jobId").orEmpty()
                ClipGeneratorScreen(jobId = jobId.ifBlank { null })
            }
            composable("social") { SocialScreen() }
            composable("settings") { SettingsScreen() }
        }
    }
}

private fun openJob(nav: NavHostController, job: StoredJob) {
    val destination = when (job.kind) {
        "shorts" -> "shorts?jobId=${job.id}"
        else -> "clips?jobId=${job.id}"
    }
    nav.navigate(destination)
}
