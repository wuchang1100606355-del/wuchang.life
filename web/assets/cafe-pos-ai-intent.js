(function () {
  "use strict";

  function tokenMatch(textValue, token) {
    var text = textValue.toUpperCase();
    var candidate = token.toUpperCase();
    if (/^[A-Z]$/.test(candidate)) {
      return (" " + text.replace(/[^A-Z0-9]+/g, " ") + " ").indexOf(" " + candidate + " ") !== -1;
    }
    return text.indexOf(candidate) !== -1;
  }

  function categoryName(menuData, categoryId) {
    var category = menuData.categories.find(function (item) {
      return item.id === categoryId;
    });
    return category ? category.label : "";
  }

  function productsFromAdi(menuData) {
    var candidateRefs = menuData.adi && Array.isArray(menuData.adi.candidateRefs)
      ? menuData.adi.candidateRefs
      : [];
    return candidateRefs.map(function (sourceRef) {
      return menuData.products.find(function (product) {
        return product.sourceRef === sourceRef;
      }) || null;
    }).filter(Boolean);
  }

  function optionTokens(question, option) {
    var tokens = [option.name, option.displayName];
    if (question.name === "尺寸") {
      if (option.displayName === "L") { tokens = tokens.concat(["大杯", "大"]); }
      if (option.displayName === "M") { tokens = tokens.concat(["中杯", "中"]); }
      if (option.displayName === "S") { tokens = tokens.concat(["小杯", "小"]); }
    }
    if (question.name === "甜度") {
      var sweetnessAliases = {
        "正常100%": ["正常糖", "全糖"],
        "少糖75%": ["少糖"],
        "半糖50%": ["半糖"],
        "微糖30%": ["微糖"],
        "無糖0%": ["無糖"],
        "多糖120%": ["多糖"]
      };
      tokens = tokens.concat(sweetnessAliases[option.displayName] || []);
    }
    return tokens.filter(function (token, index, all) {
      return token && all.indexOf(token) === index;
    });
  }

  function findProduct(textValue, menuData) {
    var adiProducts = productsFromAdi(menuData);
    var direct = adiProducts.filter(function (product) {
      return tokenMatch(textValue, product.sourceRef) ||
        tokenMatch(textValue, product.id) ||
        tokenMatch(textValue, product.sourceProductId);
    });
    if (direct.length === 1) {
      return { product: direct[0], ambiguous: [] };
    }

    var named = adiProducts.filter(function (product) {
      return textValue.indexOf(product.name) !== -1;
    });
    if (!named.length) {
      return { product: null, ambiguous: [] };
    }
    var longest = Math.max.apply(null, named.map(function (product) {
      return product.name.length;
    }));
    named = named.filter(function (product) {
      return product.name.length === longest;
    });
    if (named.length > 1) {
      var narrowed = named.filter(function (product) {
        return textValue.indexOf(product.sourceCategory) !== -1 ||
          textValue.indexOf(categoryName(menuData, product.category)) !== -1;
      });
      if (narrowed.length === 1) {
        return { product: narrowed[0], ambiguous: [] };
      }
      return { product: null, ambiguous: named };
    }
    return { product: named[0], ambiguous: [] };
  }

  function resolve(textValue, menuData, staffFlow) {
    var text = String(textValue || "").trim();
    if (!text) {
      return { status: "EMPTY_INTENT", selections: {} };
    }
    var match = findProduct(text, menuData);
    if (!match.product) {
      return {
        status: match.ambiguous.length ? "AMBIGUOUS_PRODUCT" : "UNKNOWN_PRODUCT",
        selections: {},
        ambiguous: match.ambiguous.map(function (product) {
          return {
            id: product.id,
            name: product.name,
            sourceRef: product.sourceRef,
            sourceCategory: product.sourceCategory
          };
        })
      };
    }

    var selections = {};
    var unresolved = [];
    staffFlow.questionsForProduct(menuData, match.product).forEach(function (question) {
      var matches = question.options.map(function (option) {
        var matchingTokens = optionTokens(question, option).filter(function (token) {
          return tokenMatch(text, token);
        });
        return {
          option: option,
          score: matchingTokens.reduce(function (max, token) {
            return Math.max(max, token.length);
          }, 0)
        };
      }).filter(function (candidate) {
        return candidate.score > 0;
      });
      var bestScore = matches.reduce(function (max, candidate) {
        return Math.max(max, candidate.score);
      }, 0);
      var best = matches.filter(function (candidate) {
        return candidate.score === bestScore;
      });
      if (best.length === 1) {
        selections[question.id] = best[0].option.id;
      } else if (question.required) {
        unresolved.push(question.displayName);
      }
    });

    return {
      status: unresolved.length ? "NEEDS_HUMAN_SELECTION" : "READY_FOR_HUMAN_CONFIRMATION",
      lookupSurface: "ADI",
      adiState: menuData.adi.state,
      productionAdiState: menuData.adi.productionState,
      productId: match.product.id,
      productName: match.product.name,
      sourceRef: match.product.sourceRef,
      selections: selections,
      unresolved: unresolved
    };
  }

  window.WUCHANG_CAFE_POS_AI_INTENT = Object.freeze({
    surface: "ADI_AI",
    productsFromAdi: productsFromAdi,
    resolve: resolve
  });
}());
