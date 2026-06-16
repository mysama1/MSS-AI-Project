// Kotlin VDP test file
fun main() {
    // K1: nullable deref without ?. 
    val name: String? = "test"
    println(name.length)  // should be name?.length
    
    // K2: stream leak
    val reader = FileReader("data.txt")
    
    // K3: coroutine without scope
    runBlocking {
        launch {
            println("leaked coroutine")
        }
    }
    
    // K4: throw without try-catch
    throw RuntimeException("error")
    
    // K5: URL without timeout
    val url = URL("http://example.com")
    val conn = url.openConnection()
    
    // OK: safe 
    name?.uppercase()
    FileReader("ok.txt").use { it.readText() }
}
