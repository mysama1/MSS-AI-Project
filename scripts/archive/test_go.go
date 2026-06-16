package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
)

func badCode() {
	// G1: error unchecked — single assign
	data, _ := os.ReadFile("config.txt")
	_ = data

	// G1: error unchecked — underscore discard
	resp, _ := http.Get("http://example.com")

	// G2: missing defer close on resource
	f := os.Open("data.txt")

	// G3: goroutine without context
	go func() {
		fmt.Println("leaked goroutine")
	}()

	// G4: type assertion without nil check
	var x interface{} = "hello"
	s := x.(string)
	_ = s

	// G5: HTTP without context timeout
	http.Get("http://api.example.com")
}

func goodCode() {
	// OK: proper error handling
	val, err := os.ReadFile("good.txt")
	if err != nil {
		panic(err)
	}
	_ = val

	// OK: with defer close
	f2, err := os.Open("safe.txt")
	if err != nil {
		return
	}
	defer f2.Close()

	// OK: goroutine with context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() {
		select {
		case <-ctx.Done():
			return
		}
	}()

	// OK: HTTP with context
	ctx2, cancel2 := context.WithTimeout(context.Background(), 5)
	defer cancel2()
	// http.NewRequestWithContext would be proper, but detected by nearby context var
	_ = ctx2
}
