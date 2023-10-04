"""empty message

Revision ID: c01d4ad6cb06
Revises: f7549305cdf1
Create Date: 2023-09-28 12:49:50.798473

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c01d4ad6cb06'
down_revision = 'f7549305cdf1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('experience_money', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('experience_money')

    # ### end Alembic commands ###
