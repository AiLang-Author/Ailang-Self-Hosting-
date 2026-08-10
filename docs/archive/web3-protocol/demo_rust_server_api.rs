/*
 * CONCEPTUAL API DESIGN
 * ---------------------
 * This demonstrates the developer experience for building a Web 3.0 server in Rust.
 * Notice the complete absence of REST endpoints, HTTP status codes, or client JS!
 */

use web3_server::{Server, Session, Event, Update, Tvg};
use serde_json::Value;

fn main() {
    // 1. Bind to the local Web 3.0 Unix Socket
    let mut server = Server::bind("/tmp/web3.sock").expect("Failed to bind socket");

    println!("Web 3.0 Todo Server listening...");

    // 2. Define Action Routers
    // This intercepts 'we-action="submit"' from the client's HTML
    server.on_action("submit", |session: &mut Session, event: Event| {
        
        // Parse the payload sent by the client's form
        let form_data = event.payload.get("formData").unwrap();
        let task = form_data.get("task").unwrap().as_str().unwrap();
        
        println!("Received new task: {}", task);
        
        // Generate the new HTML structural fragment
        let html_fragment = format!(
            "<ul id='task-list'>
                <li><input type='checkbox'> {}</li>
             </ul>", 
             task
        );
        
        // Generate deterministic TVG UI commands
        // e.g., showing a green "Task Saved!" toast notification
        let tvg_commands = Tvg::new()
            .text("status-toast", "Task Saved!")
            .style("status-toast")
                .fill("#00FF00")
                .opacity(1.0)
                .build()
            .visible("status-toast", true);
            
        // 3. Push the state change delta back to the client
        session.send(
            Update::new()
                .in_reply_to(event.seq)
                .region("todo-app")
                .html(html_fragment)
                .commands(tvg_commands)
        ).unwrap();
    });
    
    // Support custom actions (e.g., custom:clear-all)
    server.on_action("custom:clear-all", |session, event| {
        session.send(Update::new().region("task-list").html("")).unwrap();
    });

    // 4. Start the async event loop
    server.listen();
}