// C# VDP test file
using System;
using System.IO;
using System.Net.Http;

class Test {
    // C4: empty catch
    void BadCatch() {
        try { File.ReadAllText("x.txt"); }
        catch { }
    }
    
    // C2: missing Dispose
    void BadDispose() {
        var reader = new StreamReader("data.txt");
        Console.WriteLine(reader.ReadToEnd());
    }
    
    // C1: null deref without check
    void BadNull() {
        var result = GetData();
        Console.WriteLine(result.Length);
    }
    
    // C3: async without await
    async void BadAsync() {
        Console.WriteLine("sync");
    }
    
    // C5: HttpClient without timeout
    void BadHttp() {
        var client = new HttpClient();
        var resp = client.GetAsync("http://x.com");
    }
    
    // OK: with using
    void GoodDispose() {
        using var reader = new StreamReader("ok.txt");
    }
    
    string GetData() => "hello";
}
