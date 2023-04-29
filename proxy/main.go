package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type Current struct {
	Temp      float64 `json:"temp"`
	FeelsLike float64 `json:"feels_like"`
}

type Rain struct {
	OneH float64 `json:"1h"`
}

type Hourly struct {
	Dt   int     `json:"dt"`
	Temp float64 `json:"temp"`
	Pop  float64 `json:"pop"`
	Rain Rain    `json:"rain"`
}

type Message struct {
	TimezoneOffset int      `json:"timezone_offset"`
	Current        Current  `json:"current"`
	Hourly         []Hourly `json:"hourly"`
}

func handle(w http.ResponseWriter, r *http.Request) {
	url := fmt.Sprintf("https://api.openweathermap.org/data/3.0/onecall?%s", r.URL.RawQuery)
	fmt.Printf("%s\n", url)
	resp, err := http.Get(url)
	if err != nil {
		fmt.Println(err)
		return
	}
	defer resp.Body.Close()

	var m Message
	if err := json.NewDecoder(resp.Body).Decode(&m); err != nil {
		fmt.Println(err)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(m); err != nil {
		fmt.Println(err)
		return
	}
	fmt.Printf("OK\n")
}

func main() {
	http.HandleFunc("/", handle)
	http.ListenAndServe(":8080", nil)
}
