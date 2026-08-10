#include <stdio.h>
#include <string.h>

void extract_we_attributes(const char* html) {
    const char* p = html;
    
    while (*p) {
        // Look for the start of an HTML element
        if (*p == '<' && *(p+1) != '/') {
            p++;
            char tag[32] = {0};
            int t = 0;
            
            // Extract tag name (e.g., "button", "input")
            while (*p && *p != ' ' && *p != '>' && t < 31) {
                tag[t++] = *p++;
            }
            
            char action[64] = {0};
            char target[64] = {0};
            
            // Scan attributes until the tag closes
            while (*p && *p != '>') {
                if (strncmp(p, "we-action=\"", 11) == 0) {
                    p += 11;
                    int a = 0;
                    while (*p && *p != '"' && a < 63) action[a++] = *p++;
                } else if (strncmp(p, "we-target=\"", 11) == 0) {
                    p += 11;
                    int a = 0;
                    while (*p && *p != '"' && a < 63) target[a++] = *p++;
                }
                p++;
            }
            
            if (action[0] != '\0') {
                printf("Wired Element Found: <%s>\n", tag);
                printf("  └─ Action: %s\n", action);
                printf("  └─ Target: %s\n\n", target[0] ? target : "(default/self)");
            }
        }
        p++;
    }
}

int main() {
    const char* html_skeleton = 
        "<div class='toolbar' id='main-toolbar'>"
        "  <button we-action='submit' we-target='todo-app'>Save</button>"
        "  <input type='text' we-action='input'>"
        "  <a href='/settings' we-action='load' we-target='desktop'>Settings</a>"
        "</div>";
        
    printf("Scanning HTML for Web 3.0 wiring attributes...\n\n");
    extract_we_attributes(html_skeleton);
    
    return 0;
}