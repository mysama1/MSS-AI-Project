<?php
// Test file for PHP VDP scanner

// P3: SQL without escaping
$result = mysql_query("SELECT * FROM users WHERE name='$name'");

// P1: @ suppression operator
@file_get_contents("missing.txt");

// P2: file leak
$f = fopen("data.txt", "r");

// P5: session without security
session_start();

// OK: session with security
ini_set('session.cookie_secure', 1);
ini_set('session.cookie_httponly', 1);
session_start();

// OK: null-safe
$name = $_GET['name'] ?? 'default';
if (isset($user)) { echo $user->name; }

// P4: access without null check
echo $user->email;

// OK: prepared statement
$stmt = $db->prepare("SELECT * FROM users WHERE id=?");
