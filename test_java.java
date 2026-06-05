
import java.net.*;
import java.io.*;

// J1: unclosed resource
InputStream is = new FileInputStream("data.txt");

// J2: HTTP no timeout
URL url = new URL("http://example.com");
HttpURLConnection conn = url.openConnection();

// J3: nullable return without annotation
public String findUser(int id) {
    if (id < 0) return null;
    return "user";
}

// J1 OK: try-with-resources
try (InputStream is2 = new FileInputStream("data.txt")) {
    // safe
}
