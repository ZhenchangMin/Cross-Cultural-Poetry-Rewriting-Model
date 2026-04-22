module.exports = {
root: true,
env: {
    node: true
},
extends: [
    'plugin:vue/vue3-essential',
    'eslint:recommended'
],
parserOptions: {
    ecmaVersion: 2020
},
rules: {},

globals: {
    defineProps: "readonly",
    defineEmits: "readonly"
}
}