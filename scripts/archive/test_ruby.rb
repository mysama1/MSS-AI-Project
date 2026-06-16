#!/usr/bin/env ruby
# Test file for Ruby VDP scanner

# R3: eval danger
eval("puts 'hello'")

# R1: bare rescue
begin
  risky_operation
rescue => e
  puts "error: #{e}"  # bare rescue, R1 should flag
end

# R2: file leak — opened without close/block
f = File.open("data.txt")
puts f.read
# f.close missing

# R5: unsafe Marshal.load
data = Marshal.load(File.read("data.bin"))

# OK: File.open with block
File.open("safe.txt") do |f|
  puts f.read
end

# OK: safe navigation
user&.name
