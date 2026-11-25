package repositories

import (
	"context"
	"errors"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// UserStore is what AuthController depends on, so tests can run without Mongo.
type UserStore interface {
	Create(ctx context.Context, user models.User) error
	ByEmail(ctx context.Context, email string) (*models.User, error)
	ByID(ctx context.Context, id string) (*models.User, error)
}

type UserRepository struct {
	users *mongo.Collection
}

func NewUserRepository(db *mongo.Database) *UserRepository {
	return &UserRepository{users: db.Collection(constants.UsersCollection)}
}

func (r *UserRepository) EnsureIndexes(ctx context.Context) error {
	_, err := r.users.Indexes().CreateMany(ctx, []mongo.IndexModel{
		{Keys: bson.D{{Key: "id", Value: 1}}, Options: options.Index().SetUnique(true)},
		{Keys: bson.D{{Key: "email", Value: 1}}, Options: options.Index().SetUnique(true)},
	})
	return err
}

func (r *UserRepository) Create(ctx context.Context, user models.User) error {
	_, err := r.users.InsertOne(ctx, user)
	if mongo.IsDuplicateKeyError(err) {
		return types.ErrEmailTaken
	}
	return err
}

func (r *UserRepository) ByEmail(ctx context.Context, email string) (*models.User, error) {
	var user models.User
	err := r.users.FindOne(ctx, bson.M{"email": email}).Decode(&user)
	if err != nil {
		if errors.Is(err, mongo.ErrNoDocuments) {
			return nil, types.ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) ByID(ctx context.Context, id string) (*models.User, error) {
	var user models.User
	err := r.users.FindOne(ctx, bson.M{"id": id}).Decode(&user)
	if err != nil {
		if errors.Is(err, mongo.ErrNoDocuments) {
			return nil, types.ErrUserNotFound
		}
		return nil, err
	}
	return &user, nil
}

var _ UserStore = (*UserRepository)(nil)
