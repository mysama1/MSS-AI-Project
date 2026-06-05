
// Test V2: empty catch
try { riskyCall(); } catch (e) { }

// Test V2: Promise without catch (simplified - will catch on the outer)
fetch('url').then(r => r.json())

// This should NOT trigger V2: proper error handling
try { riskyCall(); } catch (e) { console.error(e); }

// This should NOT trigger V2: Promise with catch
fetch('url').then(r => r.json()).catch(e => console.error(e))
