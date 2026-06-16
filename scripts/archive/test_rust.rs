// R1: bare unwrap
fn get_config() -> String {
    std::env::var("CONFIG_PATH").unwrap()  // should warn
}

// R1 OK: proper error handling
fn get_config_safe() -> Result<String, std::env::VarError> {
    std::env::var("CONFIG_PATH")
}

// R2: silent discard
fn process_data() {
    let _ = std::fs::read_to_string("data.txt");  // should warn
}

// R3: unsafe without safety comment
unsafe fn raw_ptr() {
    let x = 42;
    let p: *const i32 = &x;  // unsafe fn body — should warn
}

// R3 OK: unsafe with safety comment
// SAFETY: pointer is valid within this function scope
unsafe fn raw_ptr_safe() {
    let x = 42;
    let p: *const i32 = &x;
}

// R4: HTTP without timeout
fn fetch_data() {
    let client = reqwest::Client::new();  // should warn
}

// R5: direct file write
fn save_config(data: &str) {
    std::fs::write("config.json", data).unwrap();  // should warn (R1+R5)
}
