// Package utils holds helpers with no dependency on the domain.
package utils

import (
	"fmt"
	"strings"
)

// Cents is the project's money unit: integers, never floats.
//
// Same rule as `ai/` and the front end. A table's bill either reconciles or
// it does not, and float64 loses that argument: 0.1+0.2 is not 0.3, and one
// lost cent is the difference between closing the table and not.
type Cents int64

// Display formats for humans: "$1,240" when round, "$120.50" otherwise.
func (c Cents) Display() string {
	sign := ""
	if c < 0 {
		sign = "-"
		c = -c
	}
	whole, frac := int64(c)/100, int64(c)%100
	if frac == 0 {
		return fmt.Sprintf("%s$%s", sign, withThousands(whole))
	}
	return fmt.Sprintf("%s$%s.%02d", sign, withThousands(whole), frac)
}

// Decimal renders the amount as "276.00": what a payment API expects, built
// without ever going through a float.
func (c Cents) Decimal() string {
	sign := ""
	if c < 0 {
		sign = "-"
		c = -c
	}
	return fmt.Sprintf("%s%d.%02d", sign, int64(c)/100, int64(c)%100)
}

// ParseDecimal turns "150", "120.5" or "0.01" into cents without a float.
// Pey sends the webhook amount as a JSON number in pesos, so this closes the
// circle back into the domain's unit.
func ParseDecimal(s string) (Cents, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, fmt.Errorf("empty amount")
	}

	negative := false
	switch s[0] {
	case '-':
		negative, s = true, s[1:]
	case '+':
		s = s[1:]
	}

	whole, frac, _ := strings.Cut(s, ".")
	if whole == "" {
		whole = "0"
	}
	// Pad or truncate to exactly two digits: "120.5" is 50 cents, not 5.
	frac = (frac + "00")[:2]

	var total int64
	for _, part := range []string{whole, frac} {
		for _, r := range part {
			if r < '0' || r > '9' {
				return 0, fmt.Errorf("not a decimal amount: %q", s)
			}
			total = total*10 + int64(r-'0')
		}
	}
	if negative {
		total = -total
	}
	return Cents(total), nil
}

func withThousands(n int64) string {
	s := fmt.Sprintf("%d", n)
	if len(s) <= 3 {
		return s
	}
	var groups []string
	for len(s) > 3 {
		groups = append([]string{s[len(s)-3:]}, groups...)
		s = s[:len(s)-3]
	}
	return s + "," + strings.Join(groups, ",")
}

// Split divides an amount n ways without losing a cent.
//
// Integer division leaves a remainder; it goes one cent at a time to the
// first shares. Summing the result always returns the original, which is what
// lets a table close at zero.
func Split(total Cents, ways int) []Cents {
	if ways <= 0 {
		return nil
	}
	base := total / Cents(ways)
	remainder := total - base*Cents(ways)

	shares := make([]Cents, ways)
	for i := range shares {
		shares[i] = base
		if Cents(i) < remainder {
			shares[i]++
		}
	}
	return shares
}
