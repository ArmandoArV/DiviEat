package types

// Role defines the user's role inside DiviEat.
type Role string

const (
	RoleComensal Role = "comensal"
	RoleMesero   Role = "mesero"
	RoleAdmin    Role = "admin"
)

// Valid reports whether r is one of the accepted roles.
func (r Role) Valid() bool {
	switch r {
	case RoleComensal, RoleMesero, RoleAdmin:
		return true
	default:
		return false
	}
}
