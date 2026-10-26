plugins {
    id("com.android.application")
}

android {
    enableKotlin = false
    namespace = "com.foldandtick.watchface"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.foldandtick.watchface"
        minSdk = 34
        targetSdk = 36
        versionCode = 8
        versionName = "1.4.3"
    }

    val releaseStore = providers.environmentVariable("FOLD_TICK_KEYSTORE_PATH").orNull
    if (releaseStore != null) {
        signingConfigs.create("release") {
            storeFile = file(releaseStore)
            storePassword = providers.environmentVariable("FOLD_TICK_STORE_PASSWORD").get()
            keyAlias = providers.environmentVariable("FOLD_TICK_KEY_ALIAS").get()
            keyPassword = providers.environmentVariable("FOLD_TICK_KEY_PASSWORD").get()
        }
    }

    // R8 removes generated R classes; WFF packages must contain no DEX.
    // Keep resource shrinking off: XML refers to assets by bare resource names.
    buildTypes {
        debug {
            isMinifyEnabled = true
            isShrinkResources = false
        }
        release {
            signingConfig = signingConfigs.findByName("release")
            isMinifyEnabled = true
            isShrinkResources = false
        }
    }
}
