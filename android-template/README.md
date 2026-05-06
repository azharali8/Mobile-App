# Android Template (WebView)

This folder contains a ready Android Studio project that opens your Streamlit app in a native Android WebView.

## Open in Android Studio

1. Open Android Studio.
2. Click **Open**.
3. Select this folder: `android-template`.
4. Let Gradle sync finish.

## Build APK

1. In Android Studio, go to **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
2. After build completes, click the notification link to locate the APK.

## Change deployed URL

Edit this line in `app/src/main/java/com/easypaisa/webapp/MainActivity.kt`:

`webView.loadUrl("https://mobile-app-dgzswyk8gfqb3b7any2pnk.streamlit.app/")`

Replace it with your latest Streamlit URL.
