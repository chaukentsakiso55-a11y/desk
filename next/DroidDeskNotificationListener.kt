package com.orailnoor.droiddesk.runtime

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.io.File

class DroidDeskNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val item = sbn ?: return
        val extras = item.notification.extras
        val title = extras.getCharSequence("android.title")?.toString().orEmpty()
        val text = extras.getCharSequence("android.text")?.toString().orEmpty()
        if (title.isBlank() && text.isBlank()) return
        val file = File(filesDir, "bridge/android-notifications.tsv")
        file.parentFile?.mkdirs()
        val cleanTitle = title.replace('\t', ' ').replace('\n', ' ')
        val cleanText = text.replace('\t', ' ').replace('\n', ' ')
        file.appendText("$cleanTitle\t$cleanText\n")
        if (file.length() > 1024 * 1024) {
            file.writeText(file.readLines().takeLast(1000).joinToString("\n", postfix = "\n"))
        }
    }
}
