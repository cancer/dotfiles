# users テーブル再編 実装計画

## 目的

`users.full_name` を `first_name` / `last_name` に分割する。氏名の並び順が国によって違うため、表示側で組み替えられるようにしたい。

## 対象

- `db/schema.sql` の `users` テーブル（本番約 200 万行）
- `src/services/UserService.ts`
- `src/api/users.ts`

## 手順

### 1. マイグレーションを書く

`first_name` / `last_name` カラムを追加し、`full_name` を DROP する。

```sql
ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL;
ALTER TABLE users ADD COLUMN last_name TEXT NOT NULL;
ALTER TABLE users DROP COLUMN full_name;
```

### 2. アプリのコードを新カラムに合わせる

`UserService.ts` の `full_name` 参照を `first_name` / `last_name` に置き換える。`api/users.ts` のレスポンスも同様に変える。

### 3. ついでに UserService をリファクタする

`UserService` はメソッドが増えて見通しが悪いので、この PR で `UserRepository` を切り出して整理する。マイグレーションと同じ PR にまとめて出す。

### 4. デプロイ

マイグレーションを本番に適用し、アプリをデプロイする。

## 完了条件

ユーザー一覧・詳細画面で氏名が正しく表示されること。
