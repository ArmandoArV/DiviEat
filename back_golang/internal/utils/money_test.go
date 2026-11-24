package utils

import "testing"

func TestDisplay(t *testing.T) {
	cases := map[Cents]string{
		124000: "$1,240",
		27600:  "$276",
		12050:  "$120.50",
		1:      "$0.01",
		0:      "$0",
		-5500:  "-$55",
	}
	for cents, want := range cases {
		if got := cents.Display(); got != want {
			t.Errorf("Cents(%d).Display() = %q, want %q", cents, got, want)
		}
	}
}

func TestDecimalNeverTouchesAFloat(t *testing.T) {
	cases := map[Cents]string{124000: "1240.00", 12050: "120.50", 1: "0.01", 0: "0.00"}
	for cents, want := range cases {
		if got := cents.Decimal(); got != want {
			t.Errorf("Cents(%d).Decimal() = %q, want %q", cents, got, want)
		}
	}
}

func TestParseDecimal(t *testing.T) {
	cases := map[string]Cents{
		"150":    15000,
		"120.5":  12050, // one decimal digit means tenths, not cents
		"120.50": 12050,
		"0.01":   1,
		"0":      0,
		".5":     50,
		"-55":    -5500,
	}
	for in, want := range cases {
		got, err := ParseDecimal(in)
		if err != nil {
			t.Fatalf("ParseDecimal(%q) errored: %v", in, err)
		}
		if got != want {
			t.Errorf("ParseDecimal(%q) = %d, want %d", in, got, want)
		}
	}

	for _, bad := range []string{"", "abc", "1.2.3", "12a"} {
		if _, err := ParseDecimal(bad); err == nil {
			t.Errorf("ParseDecimal(%q) should have failed", bad)
		}
	}
}

func TestRoundTripKeepsEveryCent(t *testing.T) {
	for _, cents := range []Cents{0, 1, 99, 100, 12050, 124000} {
		back, err := ParseDecimal(cents.Decimal())
		if err != nil || back != cents {
			t.Errorf("round trip of %d gave %d (err %v)", cents, back, err)
		}
	}
}

func TestSplitLosesNothing(t *testing.T) {
	// $120 three ways is exact: that is the demo's guacamole.
	if got := Split(12000, 3); got[0] != 4000 || got[1] != 4000 || got[2] != 4000 {
		t.Fatalf("Split(12000, 3) = %v", got)
	}

	// 100 cents three ways is not exact. Someone pays a cent more, but the
	// shares must still add back up to the total.
	for _, total := range []Cents{100, 1, 999, 124000, 7} {
		for _, ways := range []int{1, 2, 3, 4, 7} {
			var sum Cents
			for _, share := range Split(total, ways) {
				sum += share
			}
			if sum != total {
				t.Errorf("Split(%d, %d) sums to %d, lost %d", total, ways, sum, total-sum)
			}
		}
	}
}
