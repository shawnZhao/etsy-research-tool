"""change_etsy_ids_to_bigint

Revision ID: 18c06f550645
Revises: 0001
Create Date: 2026-05-18 07:50:24.936182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18c06f550645'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop FK that depends on shops_shop_id_key
    op.drop_constraint('listings_shop_id_fkey', 'listings', type_='foreignkey')

    # 2. Drop unique constraints / indexes before altering column types
    op.drop_index('ix_shops_shop_id', table_name='shops')
    op.drop_index('ix_listings_listing_id', table_name='listings')

    # 3. Alter Etsy ID columns to BigInteger
    op.alter_column('shops', 'shop_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    op.alter_column('listings', 'shop_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    op.alter_column('listings', 'listing_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)

    # 4. Recreate unique indexes
    op.create_index(op.f('ix_shops_shop_id'), 'shops', ['shop_id'], unique=True)
    op.create_index(op.f('ix_listings_listing_id'), 'listings', ['listing_id'], unique=True)

    # 5. Recreate FK
    op.create_foreign_key('listings_shop_id_fkey', 'listings', 'shops',
                          ['shop_id'], ['shop_id'])


def downgrade() -> None:
    # 1. Drop FK
    op.drop_constraint('listings_shop_id_fkey', 'listings', type_='foreignkey')

    # 2. Drop indexes
    op.drop_index(op.f('ix_shops_shop_id'), table_name='shops')
    op.drop_index(op.f('ix_listings_listing_id'), table_name='listings')

    # 3. Revert to Integer
    op.alter_column('shops', 'shop_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)
    op.alter_column('listings', 'shop_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)
    op.alter_column('listings', 'listing_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.INTEGER(),
                    existing_nullable=False)

    # 4. Recreate indexes
    op.create_index('ix_shops_shop_id', 'shops', ['shop_id'], unique=True)
    op.create_index('ix_listings_listing_id', 'listings', ['listing_id'], unique=True)

    # 5. Recreate FK
    op.create_foreign_key('listings_shop_id_fkey', 'listings', 'shops',
                          ['shop_id'], ['shop_id'])
