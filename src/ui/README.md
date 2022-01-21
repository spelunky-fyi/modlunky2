# Modlunky2 Web Frontend

## Environment Setup

We use [pnpm](https://pnpm.io/installation) to manage npm packages.

To install the dependencies and setup your environment run the following from this directory.

```shell
pnpm install
```

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) w/ the following extensions:

- [Svelte](https://marketplace.visualstudio.com/items?itemName=svelte.svelte-vscode)
- [ESLint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint)
- [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)

## Development

### Running Dev Server

```shell
npnm dev
```

### Formatting

We recommend you setup your editor to format on save but if you need to check/fix formatting you can use the following.

**Check Formatting**

```shell
pnpm run format-check
```

**Format Code**

```shell
pnpm run format-write
```

### Linting

To ensure we follow best practices we use ESLint. We recommend you use an IDE with an
ESLint plugin but if you need run the lint manually you can run the following.

```shell
pnpm run lint
```

### Type Checking

We use TypeScript for type checking. We recommend you use an IDE that can provide inline
type checking but if you need to check manually you can run the following.

```shell
pnpm run check
```
