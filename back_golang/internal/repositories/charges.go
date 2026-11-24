// Package repositories is the only thing that touches Mongo. If storage ever
// changes, it changes here and the controllers never notice.
package repositories

import (
	"context"
	"errors"
	"time"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"

	"github.com/ArmandoArV/DiviEat/back_golang/internal/constants"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/models"
	"github.com/ArmandoArV/DiviEat/back_golang/internal/types"
)

// ChargeStore is what the controller depends on, so tests can stand in for
// Mongo without a server.
type ChargeStore interface {
	Save(ctx context.Context, charge models.Charge) error
	ByOrder(ctx context.Context, order string) ([]models.Charge, error)
	MarkPaid(ctx context.Context, id, transactionID string) (bool, error)
}

type ChargeRepository struct {
	charges *mongo.Collection
}

func NewChargeRepository(db *mongo.Database) *ChargeRepository {
	return &ChargeRepository{charges: db.Collection(constants.ChargesCollection)}
}

func (r *ChargeRepository) EnsureIndexes(ctx context.Context) error {
	_, err := r.charges.Indexes().CreateMany(ctx, []mongo.IndexModel{
		// `id` is how a payment is confirmed; `order` is how the bill is built.
		{Keys: bson.D{{Key: "id", Value: 1}}, Options: options.Index().SetUnique(true)},
		{Keys: bson.D{{Key: "order", Value: 1}, {Key: "status", Value: 1}}},
		{Keys: bson.D{{Key: "transactionId", Value: 1}}, Options: options.Index().SetSparse(true)},
	})
	return err
}

func (r *ChargeRepository) Save(ctx context.Context, charge models.Charge) error {
	_, err := r.charges.UpdateOne(ctx,
		bson.M{"id": charge.ID},
		bson.M{"$set": charge},
		options.UpdateOne().SetUpsert(true),
	)
	return err
}

func (r *ChargeRepository) ByOrder(ctx context.Context, order string) ([]models.Charge, error) {
	cursor, err := r.charges.Find(ctx, bson.M{"order": order})
	if err != nil {
		return nil, err
	}
	charges := []models.Charge{}
	if err := cursor.All(ctx, &charges); err != nil {
		return nil, err
	}
	return charges, nil
}

// MarkPaid is idempotent on purpose, because Pey retries.
//
// The filter insists the charge is still pending, so a second delivery moves
// nothing and reports false — which is how the controller tells "just paid"
// apart from "already paid".
func (r *ChargeRepository) MarkPaid(ctx context.Context, id, transactionID string) (bool, error) {
	now := time.Now().UTC()
	result, err := r.charges.UpdateOne(ctx,
		bson.M{"id": id, "status": types.ChargePending},
		bson.M{"$set": bson.M{
			"status":        types.ChargePaid,
			"transactionId": transactionID,
			"paidAt":        now,
		}},
	)
	if err != nil {
		if errors.Is(err, mongo.ErrNoDocuments) {
			return false, types.ErrChargeNotFound
		}
		return false, err
	}
	return result.ModifiedCount == 1, nil
}

var _ ChargeStore = (*ChargeRepository)(nil)
