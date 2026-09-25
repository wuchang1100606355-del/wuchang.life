(function () {
  "use strict";

  function productFor(menuData, id) {
    return menuData.products.find(function (product) {
      return product.id === id;
    }) || null;
  }

  function optionGroupFor(menuData, id) {
    return menuData.optionGroups.find(function (group) {
      return group.id === id;
    }) || null;
  }

  function questionsForProduct(menuData, product) {
    return product.optionGroupIds.reduce(function (questions, groupId) {
      var group = optionGroupFor(menuData, groupId);
      return group ? questions.concat(group.questions) : questions;
    }, []);
  }

  function optionFor(question, optionId) {
    return question.options.find(function (option) {
      return option.id === optionId;
    }) || null;
  }

  function normalizeConfiguration(menuData, productId, rawSelections) {
    var product = productFor(menuData, productId);
    if (!product) {
      return { ok: false, code: "UNKNOWN_SOURCE_PRODUCT" };
    }

    var questions = questionsForProduct(menuData, product);
    var questionIds = questions.map(function (question) { return question.id; });
    var unknownQuestionIds = Object.keys(rawSelections).filter(function (questionId) {
      return questionIds.indexOf(questionId) === -1;
    });
    if (unknownQuestionIds.length) {
      return {
        ok: false,
        code: "UNKNOWN_SOURCE_QUESTION",
        unknownQuestionIds: unknownQuestionIds
      };
    }

    var invalidOptions = [];
    var missingQuestions = [];
    var selections = [];
    questions.forEach(function (question) {
      var optionId = rawSelections[question.id];
      if (!optionId) {
        if (question.required) {
          missingQuestions.push(question.displayName);
        }
        return;
      }
      var option = optionFor(question, optionId);
      if (!option) {
        invalidOptions.push({
          questionId: question.id,
          optionId: optionId
        });
        return;
      }
      selections.push({
        questionId: question.id,
        questionName: question.displayName,
        questionCoordinate: product.sourceRef + ":" + question.id,
        optionId: option.id,
        optionName: option.displayName,
        optionCoordinate: product.sourceRef + ":" + option.id,
        priceDelta: option.priceDelta
      });
    });
    if (invalidOptions.length) {
      return {
        ok: false,
        code: "UNKNOWN_SOURCE_OPTION",
        invalidOptions: invalidOptions
      };
    }
    if (missingQuestions.length) {
      return {
        ok: false,
        code: "REQUIRED_OPTION_MISSING",
        missingQuestions: missingQuestions,
        product: product,
        selections: selections
      };
    }

    var unitPrice = product.price + selections.reduce(function (sum, selection) {
      return sum + selection.priceDelta;
    }, 0);
    var key = product.id + "|" + selections.map(function (selection) {
      return selection.questionId + "=" + selection.optionId;
    }).join("|");
    return {
      ok: true,
      code: "SOURCE_CONFIGURATION_VERIFIED",
      product: product,
      selections: selections,
      unitPrice: unitPrice,
      lineKey: key
    };
  }

  var totalFieldRectifier = Object.freeze({
    surface: "TOTAL_FIELD_RECTIFIER",
    state: "L3_CANDIDATE_HUMAN_D8_REQUIRED",
    productFor: productFor,
    optionGroupFor: optionGroupFor,
    questionsForProduct: questionsForProduct,
    optionFor: optionFor,
    normalizeConfiguration: normalizeConfiguration
  });
  window.WUCHANG_CAFE_POS_TOTAL_FIELD_RECTIFIER = totalFieldRectifier;
  window.WUCHANG_CAFE_POS_STAFF_FLOW = totalFieldRectifier;
}());
