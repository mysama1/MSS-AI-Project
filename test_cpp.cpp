
#include <cstdlib>
#include <cstring>

void process() {
    // C1: malloc without free
    char* buf = (char*)malloc(1024);
    
    // C2: unsafe strcpy
    strcpy(buf, "user_input");
    
    // C3: null deref risk
    struct Node* n = get_node();
    n->value = 42;
    
    // C2: unsafe sprintf
    char tmp[64];
    sprintf(tmp, "value: %d", 42);
}

// C1 OK: malloc with free
void good() {
    char* p = (char*)malloc(100);
    if (p) { 
        strncpy(p, "safe", 100); 
        free(p); 
    }
}
